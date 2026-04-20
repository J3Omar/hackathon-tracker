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
        
        prompt = f"""أنت محلل ذكي متخصص في تحليل منشورات الفيسبوك لاكتشاف الهاكاثونات والمسابقات البرمجية.

النص المراد تحليله:
{post_text}

المطلوب: حلل النص وأجب بصيغة JSON فقط (بدون أي نص إضافي) كالتالي:

{{
  "is_hackathon": true/false,
  "confidence": 0.0-1.0,
  "event_name": "اسم الهاكاثون أو null",
  "event_date": "التاريخ بصيغة YYYY-MM-DD أو null",
  "location": "المكان أو null",
  "deadline": "آخر موعد للتسجيل YYYY-MM-DD أو null",
  "prizes": "الجوائز أو null",
  "requirements": "المتطلبات أو null",
  "reasoning": "سبب التصنيف"
}}

قواعد التحليل:
- is_hackathon = true إذا كان المنشور عن مسابقة برمجية، هاكاثون، competition، أو challenge
- confidence = درجة الثقة من 0 إلى 1
- استخرج التواريخ بدقة (مثال: "15 مايو" = "2025-05-15")
- location قد يكون مدينة، جامعة، أو "online"
- إذا لم تجد معلومة، ضع null

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
                
                # Add location relevance check
                analysis['location_relevant'] = self._is_location_relevant(
                    analysis.get('location', '')
                )
                
                return analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemma response: {e}")
                logger.debug(f"Response was: {response}")
                return None
        
        return None
    
    def _is_location_relevant(self, location):
        """Check if location matches target keywords"""
        if not location or not self.location_keywords:
            return True  # If no filter, all locations are relevant
        
        location_lower = location.lower()
        for keyword in self.location_keywords:
            if keyword.lower() in location_lower:
                return True
        
        # Also accept "online" events
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
            if not analysis.get('location_relevant', True):
                logger.info(f"Skipping post - location not relevant: {analysis.get('location')}")
                continue
            
            # Check if event is in the future
            event_date_str = analysis.get('event_date')
            if event_date_str:
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
