#!/usr/bin/env python3
"""
Gemma 3 Analyzer Module
Analyzes posts using Gemma 3 via LM Studio API
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GemmaAnalyzer:
    def __init__(self, lm_studio_url, location_keywords=None):
        self.lm_studio_url = lm_studio_url
        self.location_keywords = location_keywords or []
    
    def call_gemma(self, prompt, temperature=0.3, max_tokens=1000):
        """Call Gemma 3 via LM Studio API"""
        try:
            payload = {
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(
                self.lm_studio_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                logger.error(f"LM Studio API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Gemma: {e}")
            return None
    
    def analyze_post(self, post_text):
        """Analyze a post to determine if it's a hackathon"""
        
        prompt = f"""أنت محلل هاكاثونات مصري محترف. حلل النص التالي وأجب دائماً بـ JSON صالح فقط بدون أي نص إضافي:

النص المراد تحليله:
{post_text}

المطلوب:
{{
  "is_hackathon": true/false,
  "title": "اسم الفعالية",
  "date": "التاريخ بصيغة YYYY-MM-DD",
  "time": "الوقت",
  "location": "المكان",
  "prizes": "الجوائز",
  "registration_deadline": "آخر موعد للتسجيل YYYY-MM-DD",
  "registration_link": "رابط التسجيل إن وجد",
  "organizer": "الجهة المنظمة",
  "is_near_zagazig": true/false,
  "confidence": 0.0-1.0
}}

قواعد التحليل:
- is_hackathon = true فقط إذا كان المنشور يُعلن عن مسابقة برمجية أو هاكاثون **قادم** ومفتوح للتسجيل. 
- **تحذير هام جداً:** إذا كان المنشور يتحدث عن هاكاثون انتهى بالفعل (مثل: "صور من الهاكاثون"، "مبروك للفائزين"، "سعدنا بمشاركتكم"، "تغطية حدث")، يجب أن تجعل is_hackathon = false فوراً.
- is_near_zagazig = true إذا كان المكان في مصر ويمكن الوصول إليه بالسيارة من مدينة "الزقازيق" في أقل من 3 ساعات (مثل: القاهرة، المنصورة، الإسماعيلية، بنها، العاشر من رمضان) أو إذا كان الحدث "Online/أونلاين". أما إذا كان بعيداً (مثل الإسكندرية أو أسوان) أو خارج مصر اجعله false.
- ضع null لأي حقل نصي غير موجود.
أجب بـ JSON فقط:"""

        response = self.call_gemma(prompt, temperature=0.3)
        
        if response:
            try:
                # Clean response (remove markdown code blocks if present)
                response = response.strip()
                if response.startswith('```'):
                    response = response.split('```')[1]
                    if response.startswith('json'):
                        response = response[4:]
                response = response.strip()
                
                analysis = json.loads(response)
                
                # Add location relevance check is now handled via Gemma directly and _is_location_relevant
                analysis['location_relevant'] = self._is_location_relevant(
                    analysis.get('location', ''), analysis
                )
                
                return analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemma response: {e}")
                logger.debug(f"Response was: {response}")
                return None
        
        return None
    
    def _is_location_relevant(self, location, analysis):
        """Check if location matches target keywords or is near Zagazig"""
        # أولاً: نعتمد على ذكاء Gemma الجغرافي
        is_near = analysis.get('is_near_zagazig')
        if is_near is True:
            return True
            
        # ثانياً: فلترة احتياطية بالكلمات المفتاحية
        if not location or not self.location_keywords:
            return True
        
        location_lower = location.lower()
        for keyword in self.location_keywords:
            if keyword.lower() in location_lower:
                return True
        
        if 'online' in location_lower or 'أونلاين' in location_lower:
            return True
        
        return False
    
    def filter_relevant_hackathons(self, analyzed_posts, min_confidence=0.6, days_ahead=60):
        """Filter posts to get only relevant hackathons"""
        relevant = []
        today = datetime.now().date()
        future_limit = today + timedelta(days=days_ahead)
        
        for post in analyzed_posts:
            analysis = post.get('analysis', {})
            
            # Check if it's a hackathon with high confidence
            if not analysis.get('is_hackathon', False):
                continue
            
            if analysis.get('confidence', 0) < min_confidence:
                continue
            
            # Check if location is relevant
            if not self._is_location_relevant(analysis.get('location', ''), analysis):
                logger.info(f"Skipping post - location not relevant/too far: {analysis.get('location')}")
                continue
            
            # Check if event is in the future
            event_date_str = analysis.get('date')
            if event_date_str and event_date_str != 'null':
                try:
                    event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
                    if event_date < today or event_date > future_limit:
                        logger.info(f"Skipping post - event date out of range: {event_date}")
                        continue
                except ValueError:
                    pass  # Invalid date format, keep the post anyway
            
            relevant.append(post)
        
        logger.info(f"Filtered to {len(relevant)} relevant hackathons")
        return relevant


def test_analyzer():
    """Test the analyzer"""
    from dotenv import load_dotenv
    load_dotenv()
    
    lm_studio_url = os.getenv('LM_STUDIO_URL')
    
    test_post = """
    🎉 إعلان هام! 🎉
    
    GDG Delta تعلن عن هاكاثون البرمجة السنوي!
    
    📅 التاريخ: 15 مايو 2025
    📍 المكان: جامعة الزقازيق
    💰 الجوائز: 10,000 جنيه للفريق الفائز
    ⏰ آخر موعد للتسجيل: 1 مايو 2025
    
    المتطلبات:
    - فرق من 3-5 أفراد
    - خبرة في البرمجة
    
    سجل الآن من الرابط في التعليقات!
    """
    
    analyzer = GemmaAnalyzer(lm_studio_url, location_keywords=['زقازيق', 'delta'])
    analysis = analyzer.analyze_post(test_post)
    
    if analysis:
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
    else:
        print("Analysis failed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_analyzer()
