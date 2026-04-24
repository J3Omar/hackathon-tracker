#!/usr/bin/env python3
"""
Gemma 3 Analyzer Module
Analyzes posts using Gemma 3 via LM Studio API with:
- Keyword pre-filter (skip irrelevant posts before LLM)
- Robust JSON extraction (regex-based, handles all fence styles)
- Retry logic with exponential backoff
- geopy-based distance calculation from Zagazig
- Expanded Arabic/English prompt with explicit city list
"""

import os
import re
import json
import time
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Geographic data — Egyptian cities with GPS coordinates
# Distance threshold from Zagazig (30.5877°N, 31.5020°E)
# ---------------------------------------------------------------------------
ZAGAZIG_COORDS = (30.5877, 31.5020)
MAX_DISTANCE_KM = 300  # ≈ 3-hour drive limit

# Known Egyptian cities / venues with approximate coordinates
EGYPT_CITIES = {
    # Near Zagazig (Sharqia) — always PASS
    "الزقازيق": (30.5877, 31.5020),
    "زقازيق": (30.5877, 31.5020),
    "zagazig": (30.5877, 31.5020),
    "الشرقية": (30.5877, 31.5020),
    "sharqia": (30.5877, 31.5020),
    "العاشر من رمضان": (30.3000, 31.7500),
    "10th of ramadan": (30.3000, 31.7500),
    "بلبيس": (30.8667, 31.5583),
    "bilbeis": (30.8667, 31.5583),
    # Qalyubia
    "بنها": (30.4667, 31.1833),
    "benha": (30.4667, 31.1833),
    "القليوبية": (30.4667, 31.1833),
    "شبرا الخيمة": (30.1242, 31.2424),
    "shoubra el kheima": (30.1242, 31.2424),
    "قليوب": (30.1833, 31.2000),
    # Greater Cairo
    "القاهرة": (30.0444, 31.2357),
    "cairo": (30.0444, 31.2357),
    "مصر الجديدة": (30.0912, 31.3381),
    "heliopolis": (30.0912, 31.3381),
    "مدينة نصر": (30.0701, 31.3326),
    "nasr city": (30.0701, 31.3326),
    "المعادي": (29.9602, 31.2569),
    "maadi": (29.9602, 31.2569),
    "التجمع الخامس": (30.0200, 31.4700),
    "new cairo": (30.0200, 31.4700),
    "القاهرة الجديدة": (30.0200, 31.4700),
    "مدينتي": (30.1667, 31.5667),
    "madinaty": (30.1667, 31.5667),
    "الجيزة": (30.0131, 31.2089),
    "giza": (30.0131, 31.2089),
    "6 أكتوبر": (29.9333, 30.9333),
    "6th october": (29.9333, 30.9333),
    "أوبور": (30.2000, 31.4833),
    "obour": (30.2000, 31.4833),
    # Dakahlia / Mansoura
    "المنصورة": (31.0425, 31.3778),
    "mansoura": (31.0425, 31.3778),
    "الدقهلية": (31.0425, 31.3778),
    "dakahlia": (31.0425, 31.3778),
    "ميت غمر": (30.7167, 31.2500),
    "mit ghamr": (30.7167, 31.2500),
    # Gharbiya / Tanta
    "طنطا": (30.7865, 31.0004),
    "tanta": (30.7865, 31.0004),
    "الغربية": (30.7865, 31.0004),
    "gharbiya": (30.7865, 31.0004),
    # Kafr El Sheikh
    "كفر الشيخ": (31.1073, 30.9395),
    "kafr el sheikh": (31.1073, 30.9395),
    # Ismailia
    "الإسماعيلية": (30.5965, 32.2715),
    "اسماعيلية": (30.5965, 32.2715),
    "ismailia": (30.5965, 32.2715),
    # Suez
    "السويس": (29.9668, 32.5498),
    "suez": (29.9668, 32.5498),
    # Port Said
    "بورسعيد": (31.2565, 32.2841),
    "port said": (31.2565, 32.2841),
    # Damietta
    "دمياط": (31.4165, 31.8133),
    "damietta": (31.4165, 31.8133),
    # Menoufia
    "المنوفية": (30.5965, 30.9876),
    "menoufia": (30.5965, 30.9876),
    "شبين الكوم": (30.5667, 31.0000),
    "shebin el kom": (30.5667, 31.0000),
    # Alexandria — FAR (~230 km)
    "الإسكندرية": (31.2001, 29.9187),
    "اسكندرية": (31.2001, 29.9187),
    "alexandria": (31.2001, 29.9187),
    # Assiut — FAR (~370 km)
    "أسيوط": (27.1809, 31.1837),
    "assiut": (27.1809, 31.1837),
    # Luxor — FAR
    "الأقصر": (25.6872, 32.6396),
    "luxor": (25.6872, 32.6396),
    # Aswan — FAR
    "أسوان": (24.0889, 32.8998),
    "aswan": (24.0889, 32.8998),
}

# ---------------------------------------------------------------------------
# Keyword pre-filter — must contain at least one of these to go to Gemma
# ---------------------------------------------------------------------------
HACKATHON_PREFILTER_KEYWORDS = [
    # Arabic
    "هاكاثون", "هاكثون", "هاكاثن", "hackathon",
    "مسابقة برمجية", "مسابقة تقنية", "تحدي برمجي", "تحدي تقني",
    "مسابقة الابتكار", "innovation challenge", "مسابقة ريادة",
    "كود ماراثون", "code marathon", "كودثون", "codathon",
    "datathon", "داتاثون", "ideathon", "ايدياثون",
    "startup weekend", "ستارتب ويكند",
    "مسابقة", "competition", "تسجيل الآن", "سجل الآن",
    "register now", "التسجيل مفتوح", "فتح باب التسجيل",
    "انضم إلينا", "شارك معنا في", "CTF", "capture the flag",
    "ICPC", "جائزة", "جوائز", "prize", "prizes",
    "فرق من", "فريق من", "team of", "teams of",
    "boot camp", "bootcamp", "بوت كامب", "تدريب مكثف",
    "معسكر", "معسكر تدريبي", "معسكر توليد الأفكار",
    "AI challenge", "تحدي الذكاء الاصطناعي", "تحدي AI",
]

PREFILTER_NEGATIVE_KEYWORDS = [
    "مبروك للفائزين", "تهنئة الفائزين", "صور من الهاكاثون",
    "ختام الهاكاثون", "نتائج المسابقة", "الفائز هو",
    "تغطية حدث", "highlights", "recap", "وصل إلى النهائي",
    "شكراً للمشاركين",
]


def _haversine_distance(coord1, coord2):
    """Calculate distance in km between two (lat, lon) tuples using Haversine."""
    import math
    lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
    lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return 6371 * c  # Earth radius in km


def _city_distance_from_zagazig(location_text: str):
    """
    Try to find a known Egyptian city in the location text and return distance in km.
    Returns None if no known city matched.
    """
    if not location_text:
        return None
    loc_lower = location_text.lower()
    best_dist = None
    for city_key, coords in EGYPT_CITIES.items():
        if city_key.lower() in loc_lower:
            dist = _haversine_distance(ZAGAZIG_COORDS, coords)
            if best_dist is None or dist < best_dist:
                best_dist = dist
    return best_dist


class GemmaAnalyzer:
    def __init__(self, lm_studio_url, location_keywords=None):
        self.lm_studio_url = lm_studio_url
        self.location_keywords = location_keywords or []

    # ------------------------------------------------------------------
    # LLM call with retry
    # ------------------------------------------------------------------
    def call_gemma(self, prompt, temperature=0.2, max_tokens=1200, retries=2):
        """Call Gemma 3 via LM Studio API with retry on failure."""
        for attempt in range(retries + 1):
            try:
                payload = {
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "أنت محلل بيانات متخصص في الفعاليات التقنية المصرية. "
                                "مهمتك الوحيدة هي تحليل المنشورات وإخراج JSON صالح فقط — "
                                "لا تضف أي نص قبله أو بعده، ولا markdown، ولا شرح."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                response = requests.post(
                    self.lm_studio_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=90,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    logger.error(
                        f"LM Studio API error (attempt {attempt+1}): {response.status_code} — {response.text[:200]}"
                    )

            except requests.exceptions.Timeout:
                logger.warning(f"Gemma timeout on attempt {attempt+1}")
            except Exception as e:
                logger.error(f"Error calling Gemma (attempt {attempt+1}): {e}")

            if attempt < retries:
                wait = 2 ** attempt  # 1s, 2s
                logger.info(f"Retrying in {wait}s...")
                time.sleep(wait)

        return None

    # ------------------------------------------------------------------
    # JSON extraction — handles all fence styles + raw JSON
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_json(text: str) -> dict | None:
        """Robustly extract a JSON object from an LLM response."""
        if not text:
            return None

        text = text.strip()

        # 1. Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Strip markdown fences (```json ... ``` or ``` ... ```)
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            try:
                return json.loads(fence_match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. Find first {...} block anywhere
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    # ------------------------------------------------------------------
    # Keyword pre-filter — skip obvious non-hackathon posts
    # ------------------------------------------------------------------
    @staticmethod
    def _prefilter_post(text: str) -> bool:
        """
        Returns True if the post is worth sending to Gemma.
        Quick keyword scan — avoids wasting LLM calls on irrelevant posts.
        """
        text_lower = text.lower()

        # Reject posts that are clearly about past events
        for neg in PREFILTER_NEGATIVE_KEYWORDS:
            if neg.lower() in text_lower:
                logger.debug(f"Pre-filter rejected (negative keyword: {neg})")
                return False

        # Must contain at least one hackathon-related term
        for kw in HACKATHON_PREFILTER_KEYWORDS:
            if kw.lower() in text_lower:
                return True

        return False

    # ------------------------------------------------------------------
    # Main analysis
    # ------------------------------------------------------------------
    def analyze_post(self, post_text: str) -> dict | None:
        """Analyze a post to determine if it's a hackathon announcement."""

        # Sanitise input — truncate to 3000 chars to avoid prompt injection bloat
        safe_text = post_text.strip()[:3000]
        # Remove any JSON-breaking characters from user content
        safe_text = safe_text.replace("```", "'''")

        # Pre-filter: skip post if obviously irrelevant
        if not self._prefilter_post(safe_text):
            logger.info("Post skipped by pre-filter (no hackathon keywords found)")
            return None

        # Build the cities hint for the prompt
        near_cities = (
            "الزقازيق، بنها، المنصورة، القاهرة، الجيزة، الإسماعيلية، "
            "طنطا، دمياط، بورسعيد، السويس، كفر الشيخ، شبين الكوم، "
            "العاشر من رمضان، أوبور، مدينتي، التجمع الخامس، مصر الجديدة، "
            "6 أكتوبر، شبرا الخيمة، Cairo, Giza, Mansoura, Tanta, Ismailia, "
            "Benha, Suez, Port Said, Damietta, Obour, Nasr City, Zagazig"
        )
        far_cities = (
            "الإسكندرية, أسيوط, أسوان, الأقصر, سوهاج, قنا, "
            "المنيا, بني سويف, الفيوم, مرسى مطروح, البحر الأحمر, "
            "Alexandria, Assiut, Aswan, Luxor, Sohag"
        )

        prompt = f"""أنت محلل هاكاثونات مصري متخصص. حلل المنشور أدناه وأخرج JSON صالح فقط.

=== المنشور ===
{safe_text}
=== نهاية المنشور ===

أخرج JSON بالشكل التالي بدقة — لا تضف أي نص خارجه:

{{
  "is_hackathon": true,
  "title": "اسم الفعالية بالكامل",
  "description": "وصف مختصر للفعالية",
  "date": "YYYY-MM-DD أو null",
  "time": "الوقت مثل 10:00 AM أو null",
  "location": "المكان التفصيلي أو null",
  "online_or_onsite": "online | onsite | hybrid | unknown",
  "prizes": "الجوائز أو null",
  "registration_deadline": "YYYY-MM-DD أو null",
  "registration_link": "رابط كامل يبدأ بـ https:// أو null",
  "organizer": "اسم الجهة المنظمة أو null",
  "team_size": "مثل 2-4 أو null",
  "eligibility": "مثل طلاب جامعيين أو الجميع أو null",
  "is_near_zagazig": true,
  "confidence": 0.85
}}

قواعد صارمة:
1. is_hackathon = true فقط إذا كان المنشور يُعلن عن مسابقة/هاكاثون/تحدي تقني **قادم** مفتوح للتسجيل الآن.
2. is_hackathon = false إذا كان المنشور عن: نتائج / صور ختامية / تهنئة فائزين / إعلان وظيفة / مقال / دورة تدريبية عادية / نشرة إخبارية / إعلان تجاري.
3. confidence: اتبع هذا الدليل الدقيق:
   - 0.9-1.0: يذكر صراحةً هاكاثون/مسابقة + تاريخ + رابط تسجيل
   - 0.7-0.89: يذكر هاكاثون + بعض التفاصيل بدون رابط
   - 0.5-0.69: يُلمّح إلى مسابقة لكن التفاصيل ناقصة
   - أقل من 0.5: غير متأكد
4. is_near_zagazig = true إذا: (أ) المكان Online/أونلاين، أو (ب) المكان في إحدى المدن القريبة: {near_cities}
5. is_near_zagazig = false إذا كان المكان في: {far_cities} أو خارج مصر.
6. registration_link: يجب أن يكون رابطاً كاملاً (https://...). إذا كان في النص "الرابط في التعليقات" اكتب null.
7. date و registration_deadline: صيغة YYYY-MM-DD فقط. إذا ذُكر الشهر باللغة العربية (مثل "15 مايو 2025") حوّله للصيغة الرقمية.
8. ضع null (وليس "" أو "غير محدد") لأي حقل غير موجود في المنشور.

JSON فقط:"""

        response = self.call_gemma(prompt, temperature=0.2, max_tokens=1200)

        if response:
            analysis = self._extract_json(response)
            if analysis:
                # Normalise types
                analysis["is_hackathon"] = bool(analysis.get("is_hackathon", False))
                analysis["is_near_zagazig"] = bool(analysis.get("is_near_zagazig", False))
                try:
                    analysis["confidence"] = float(analysis.get("confidence", 0.0))
                except (TypeError, ValueError):
                    analysis["confidence"] = 0.0

                # Override/augment is_near_zagazig with geopy distance
                location = analysis.get("location") or ""
                online = str(analysis.get("online_or_onsite", "")).lower()
                if "online" in online or "أونلاين" in location.lower() or "اونلاين" in location.lower():
                    analysis["is_near_zagazig"] = True
                    analysis["distance_from_zagazig_km"] = 0
                else:
                    dist = _city_distance_from_zagazig(location)
                    if dist is not None:
                        analysis["distance_from_zagazig_km"] = round(dist, 1)
                        analysis["is_near_zagazig"] = dist <= MAX_DISTANCE_KM
                    else:
                        analysis["distance_from_zagazig_km"] = None

                # Compute location_relevant
                analysis["location_relevant"] = self._is_location_relevant(location, analysis)

                return analysis
            else:
                logger.error("Failed to extract JSON from Gemma response")
                logger.debug(f"Raw response: {response[:300]}")
                return None

        return None

    # ------------------------------------------------------------------
    # Location relevance
    # ------------------------------------------------------------------
    def _is_location_relevant(self, location: str, analysis: dict) -> bool:
        """
        Multi-layer location check:
        1. Online → always relevant
        2. geopy distance (distance_from_zagazig_km field)
        3. Gemma's is_near_zagazig
        4. Fallback: .env LOCATION_KEYWORDS
        """
        location = location or ""

        # 1. Online events always pass
        online = str(analysis.get("online_or_onsite", "")).lower()
        if "online" in online:
            return True
        if "online" in location.lower() or "أونلاين" in location or "اونلاين" in location:
            return True

        # 2. geopy distance
        dist = analysis.get("distance_from_zagazig_km")
        if dist is not None:
            return dist <= MAX_DISTANCE_KM

        # 3. Gemma's assessment
        if analysis.get("is_near_zagazig") is True:
            return True

        # 4. Fallback keyword match (from .env LOCATION_KEYWORDS)
        if self.location_keywords:
            loc_lower = location.lower()
            for kw in self.location_keywords:
                if kw.lower() in loc_lower:
                    return True

        # 5. If no location detected at all, keep the post (don't discard)
        if not location or location.lower() == "null":
            return True

        return False

    # ------------------------------------------------------------------
    # Final filter
    # ------------------------------------------------------------------
    def filter_relevant_hackathons(self, analyzed_posts, min_confidence=0.6, days_ahead=60):
        """Filter posts to get only relevant future hackathons near Zagazig."""
        relevant = []
        today = datetime.now().date()
        future_limit = today + timedelta(days=days_ahead)

        for post in analyzed_posts:
            analysis = post.get("analysis", {})

            # Must be identified as a hackathon
            if not analysis.get("is_hackathon", False):
                continue

            # Must meet confidence threshold
            if analysis.get("confidence", 0) < min_confidence:
                logger.info(
                    f"Skipping post — low confidence: {analysis.get('confidence')} "
                    f"(min={min_confidence})"
                )
                continue

            # Location must be relevant
            if not self._is_location_relevant(analysis.get("location", ""), analysis):
                dist = analysis.get("distance_from_zagazig_km")
                dist_str = f"{dist} km" if dist is not None else "unknown"
                logger.info(
                    f"Skipping post — location too far or irrelevant: "
                    f"{analysis.get('location')} ({dist_str})"
                )
                continue

            # Event date must be in the future and within days_ahead
            event_date_str = analysis.get("date")
            if event_date_str and event_date_str != "null":
                try:
                    event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
                    if event_date < today:
                        logger.info(f"Skipping post — event already passed: {event_date}")
                        continue
                    if event_date > future_limit:
                        logger.info(f"Skipping post — event too far in future: {event_date}")
                        continue
                except ValueError:
                    pass  # Unknown date format — keep the post

            relevant.append(post)

        logger.info(f"Filtered to {len(relevant)} relevant hackathons out of {len(analyzed_posts)} analyzed")
        return relevant


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
def test_analyzer():
    """Quick local test of the analyzer."""
    from dotenv import load_dotenv
    load_dotenv()

    lm_studio_url = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1/chat/completions")

    test_posts = [
        # Should be: hackathon, near Zagazig, high confidence
        """
        🎉 إعلان هام! GDG Delta تعلن عن هاكاثون البرمجة السنوي!
        📅 التاريخ: 15 مايو 2025
        📍 المكان: جامعة الزقازيق
        💰 الجوائز: 10,000 جنيه للفريق الفائز
        ⏰ آخر موعد للتسجيل: 1 مايو 2025
        🔗 سجل الآن: https://forms.gle/example123
        فرق من 3-5 أفراد — الجميع مدعو للمشاركة!
        """,
        # Should be: NOT a hackathon (past event recap)
        """
        صور من ختام هاكاثون GDG Delta 🎊
        مبروك للفائزين! شكراً لجميع المشاركين على هذا اليوم الرائع.
        """,
        # Should be: hackathon, online, high confidence
        """
        انضم إلى تحدي الذكاء الاصطناعي AI Challenge Egypt 2025!
        المسابقة أونلاين — يمكنك المشاركة من أي مكان في مصر.
        الجائزة الأولى: 5000 جنيه + شهادات معتمدة
        سجل الآن: https://ai-challenge.eg/register
        آخر موعد: 20 مايو 2025
        """,
    ]

    analyzer = GemmaAnalyzer(lm_studio_url)

    for i, text in enumerate(test_posts, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}:")
        print(f"{'='*60}")
        analysis = analyzer.analyze_post(text)
        if analysis:
            print(json.dumps(analysis, indent=2, ensure_ascii=False))
        else:
            print("Skipped (pre-filter) or analysis failed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_analyzer()
