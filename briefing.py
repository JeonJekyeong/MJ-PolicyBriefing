import os
import re
import requests
import holidays
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta

# ─── 설정 ───────────────────────────────────────────────────────
BREVO_API_KEY = os.environ['BREVO_API_KEY']
SENDER_EMAIL  = os.environ['SENDER_EMAIL']
SENDER_NAME   = os.environ['SENDER_NAME']

KST        = timezone(timedelta(hours=9))
TODAY_DT   = datetime.now(KST)
TODAY      = TODAY_DT.strftime('%Y년 %m월 %d일')
TODAY_DATE = TODAY_DT.date()

# ─── 평일·공휴일 체크 ───────────────────────────────────────────
def is_send_day():
    if TODAY_DATE.weekday() >= 5:                          # 토(5)·일(6)
        return False, '주말'
    kr = holidays.KoreaHolidayCalendar() if hasattr(holidays, 'KoreaHolidayCalendar') \
         else holidays.country_holidays('KR', years=TODAY_DATE.year)
    if TODAY_DATE in kr:
        return False, f'공휴일 ({kr[TODAY_DATE]})'
    return True, '평일'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9',
}

# ─── 공통 유틸 ──────────────────────────────────────────────────
def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = 'utf-8'
        return r.text
    except Exception as e:
        print(f'  fetch 오류 ({url}): {e}')
        return ''

def parse_rows(html):
    soup = BeautifulSoup(html, 'html.parser')
    rows = soup.find_all('tr')
    results = []
    for row in rows:
        text = re.sub(r'\s+', ' ', row.get_text(' ', strip=True))
        if re.search(r'\d{4}[-./]\d{2}[-./]\d{2}', text) and 20 < len(text) < 300:
            results.append(text.strip())
    return results

def parse_links_text(html, keyword=''):
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    for a in soup.find_all('a', string=True):
        text = a.get_text(strip=True)
        if len(text) > 8 and (not keyword or keyword in text):
            items.append(text)
    return list(dict.fromkeys(items))

# ─── 사이트별 수집 ──────────────────────────────────────────────

def scrape_hikorea():
    html = fetch('https://www.hikorea.go.kr/board/BoardNtcListR.pt?BBS_SEQ=1&BBS_GB_CD=BS10')
    rows = parse_rows(html)
    return rows[:10] or ['공지사항 수집 불가 — hikorea.go.kr 직접 확인 요망']

def scrape_immigration():
    html = fetch('https://www.immigration.go.kr/immigration/1569/subview.do')
    rows = parse_rows(html)
    return rows[:7] or ['통계 수집 불가 — immigration.go.kr 직접 확인 요망']

def scrape_losims():
    html = fetch('https://www.losims.go.kr')
    rows = parse_rows(html)
    return rows[:8] or ['공모사업 수집 불가 — losims.go.kr 직접 확인 요망']

def scrape_ncas():
    html = fetch('https://www.ncas.or.kr')
    rows = parse_rows(html)
    if rows:
        return rows[:8]
    soup = BeautifulSoup(html, 'html.parser')
    items = [a.get_text(strip=True) for a in soup.find_all('a') if len(a.get_text(strip=True)) > 10]
    return list(dict.fromkeys(items))[:8] or ['지원사업 수집 불가 — ncas.or.kr 직접 확인 요망']

def scrape_bizinfo():
    html = fetch('https://www.bizinfo.go.kr')
    rows = parse_rows(html)
    if rows:
        return rows[:8]
    items = parse_links_text(html)
    return items[:8] or ['공고 수집 불가 — bizinfo.go.kr 직접 확인 요망']

def scrape_social_enterprise():
    html = fetch('https://www.socialenterprise.or.kr/social/board/notice/list.do')
    rows = parse_rows(html)
    if rows:
        return rows[:6]
    html2 = fetch('https://www.socialenterprise.or.kr')
    items = parse_links_text(html2)
    return items[:6] or ['공고 수집 불가 — socialenterprise.or.kr 직접 확인 요망']

def scrape_kotra():
    html = fetch('https://www.kotra.or.kr')
    rows = parse_rows(html)
    if rows:
        return rows[:6]
    items = parse_links_text(html)
    return items[:6] or ['공고 수집 불가 — kotra.or.kr 직접 확인 요망']

def scrape_kstartup():
    html = fetch('https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do')
    rows = parse_rows(html)
    if rows:
        return rows[:8]
    items = parse_links_text(html)
    return items[:8] or ['공고 수집 불가 — k-startup.go.kr 직접 확인 요망']

def scrape_korea():
    html = fetch('https://korea.kr/briefing/pressReleaseList.do')
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style']):
        tag.decompose()
    text = re.sub(r'\s+', ' ', soup.get_text())
    snippets = []
    for m in re.finditer(r'20\d{2}[.\-]\d{2}[.\-]\d{2}', text):
        start = max(0, m.start() - 60)
        end   = min(len(text), m.end() + 130)
        snippets.append(text[start:end].strip())
    return snippets[:10] or ['보도자료 수집 불가 — korea.kr 직접 확인 요망']

def scrape_hometax():
    today_dt = datetime.now(KST)
    if today_dt.month == 4 and today_dt.day == 30:
        return [
            '⚠ 오늘(4월 30일) = 12월 결산 공익법인 결산서류 공시 마감일',
            '대상: 모든 공익법인 (종교단체 제외) | 미공시 시 가산세 0.5% 부과',
            '공시 주소: teht.hometax.go.kr | 문의: ☎ 126',
        ]
    return [
        '공익법인 결산서류 공시: 사업연도 종료 후 4개월 이내 홈택스 제출 의무',
        '12월 결산법인 마감: 매년 4월 30일 | 공시: teht.hometax.go.kr | ☎ 126',
    ]

def scrape_mois():
    html = fetch('https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardList.do?bbsId=BBSMSTR_000000000058')
    rows = parse_rows(html)
    return rows[:6] or ['공지 수집 불가 — mois.go.kr 직접 확인 요망']

# ─── HTML 이메일 생성 ────────────────────────────────────────────

def build_section(num, title, site, items, urgent=False):
    color  = '#c53030' if urgent else '#2c5282'
    border = '#c53030' if urgent else '#4299e1'
    star   = ' ★' if urgent else ''

    html  = f'<div style="margin-bottom:20px;padding-bottom:16px;border-bottom:1px solid #e2e8f0">'
    html += (f'<h2 style="color:{color};font-size:14px;font-weight:bold;margin:0 0 8px;'
             f'border-left:4px solid {border};padding-left:10px">'
             f'[{num}] {title}{star} '
             f'<span style="font-size:11px;color:#a0aec0;font-weight:normal">{site}</span></h2>')

    for item in items:
        is_urgent = any(k in item for k in ['마감', '임박', '★', '긴급', '⚠', '오늘'])
        c = '#c53030' if is_urgent else '#4a5568'
        w = 'bold'   if is_urgent else 'normal'
        safe = item.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        html += (f'<p style="margin:3px 0 3px 14px;color:{c};font-weight:{w};'
                 f'font-size:13px;line-height:1.6">• {safe}</p>')

    html += '</div>'
    return html

def build_email(sections_html):
    return f'''
<div style="font-family:'Malgun Gothic',Arial,sans-serif;max-width:720px;margin:0 auto;
            padding:20px;color:#2d3748;font-size:14px;line-height:1.8;background:#f7fafc">

  <div style="background:linear-gradient(135deg,#2c5282,#2b6cb0);color:white;
              padding:22px 26px;border-radius:10px;margin-bottom:24px">
    <h1 style="margin:0;font-size:22px;font-weight:bold">📋 정책 브리핑 — {TODAY}</h1>
    <p style="margin:6px 0 0;font-size:12px;opacity:0.85">
      11개 정부·공공기관 사이트 자동 수집 | {SENDER_NAME}
    </p>
  </div>

  <div style="background:white;padding:24px 28px;border-radius:10px;
              box-shadow:0 2px 8px rgba(0,0,0,0.08)">
    {''.join(sections_html)}
  </div>

  <p style="color:#a0aec0;font-size:11px;text-align:center;margin-top:20px">
    본 브리핑은 Claude Code가 자동 수집·요약한 내용입니다.
    공고별 세부 조건 및 서류는 각 기관 원문을 반드시 확인하세요.
  </p>
</div>'''

# ─── 수신자 목록 (Brevo Contacts) ───────────────────────────────

def get_recipients():
    try:
        res = requests.get(
            'https://api.brevo.com/v3/contacts',
            headers={'api-key': BREVO_API_KEY, 'Accept': 'application/json'},
            params={'limit': 100},
            timeout=10
        )
        contacts = res.json().get('contacts', [])
        return [{'email': c['email']} for c in contacts if not c.get('emailBlacklisted')]
    except Exception as e:
        print(f'수신자 조회 오류: {e}')
        return []

# ─── 이메일 발송 ─────────────────────────────────────────────────

def send_email(recipients, subject, html):
    payload = {
        'sender':      {'name': SENDER_NAME, 'email': SENDER_EMAIL},
        'to':          recipients,
        'subject':     subject,
        'htmlContent': html,
    }
    res = requests.post(
        'https://api.brevo.com/v3/smtp/email',
        headers={
            'api-key': BREVO_API_KEY,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        json=payload,
        timeout=20
    )
    return res.status_code, res.json()

# ─── 메인 ────────────────────────────────────────────────────────

def main():
    send, reason = is_send_day()
    if not send:
        print(f'[{TODAY}] 발송 건너뜀 — {reason}')
        return
    print(f'[{TODAY}] 정책 브리핑 수집 시작')

    sites = [
        (1,  '출입국/체류 — 하이코리아',        'hikorea.go.kr',           scrape_hikorea,           True),
        (2,  '출입국/체류 — 출입국정책본부',     'immigration.go.kr',        scrape_immigration,       False),
        (3,  '지방보조금 — 보탬e',             'losims.go.kr',             scrape_losims,            False),
        (4,  '문화예술 — NCAS',              'ncas.or.kr',              scrape_ncas,              False),
        (5,  '기업지원 — 기업마당',             'bizinfo.go.kr',            scrape_bizinfo,           False),
        (6,  '사회적경제 — 사회적기업진흥원',    'socialenterprise.or.kr',   scrape_social_enterprise, False),
        (7,  '수출/투자 — KOTRA',            'kotra.or.kr',             scrape_kotra,             False),
        (8,  '창업/벤처 — K-Startup',        'k-startup.go.kr',          scrape_kstartup,          False),
        (9,  '법령/정책 — 정책브리핑',          'korea.kr',                scrape_korea,             False),
        (10, '비영리/공익 — 홈택스 공익법인',   'hometax.go.kr',            scrape_hometax,           False),
        (11, '비영리/공익 — 행정안전부',        'mois.go.kr',              scrape_mois,              False),
    ]

    sections_html = []
    for num, title, site, fn, urgent in sites:
        print(f'  [{num:02d}] {site} 수집 중...')
        items = fn()
        sections_html.append(build_section(num, title, site, items, urgent))

    html       = build_email(sections_html)
    recipients = get_recipients()

    if not recipients:
        print('수신자 없음 — 발송 중단')
        return

    print(f'수신자: {[r["email"] for r in recipients]}')
    status, result = send_email(recipients, f'[정책 브리핑] {TODAY}', html)
    print(f'발송 완료 | status={status} | messageId={result.get("messageId", result)}')

if __name__ == '__main__':
    main()
