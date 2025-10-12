# PRD: HN Summary & Translate

## 1. 제품 개요

### 1.1 프로젝트명
**HN RSS Translator** - Hacker News RSS 자동 요약 및 번역 서비스

### 1.2 목적
Hacker News의 RSS 피드를 주기적으로 수집하여, 무료 AI 라이브러리를 통해 각 항목을 요약하고 사용자가 지정한 언어로 번역한 후, 새로운 RSS 피드로 제공하는 완전 무료 오픈소스 도구

### 1.3 핵심 가치
- **완전 무료 운영**: 무료 AI 라이브러리와 GitHub 인프라만 사용
- **서버리스 아키텍처**: GitHub Actions와 GitHub Pages로 완전 자동화
- **간단한 설치**: Fork 후 최소한의 설정으로 즉시 사용 가능
- **오픈소스 우선**: 누구나 기여하고 개선할 수 있는 구조

## 2. 기술 스택

### 2.1 인프라
- **실행 환경**: GitHub Actions (무료 티어)
- **호스팅**: GitHub Pages (정적 파일 호스팅)
- **비밀 관리**: GitHub Secrets

### 2.2 핵심 라이브러리
```
feedparser          # RSS 파싱
requests            # HTTP 요청
deep-translator     # 무료 번역 (Google Translate)
transformers        # Hugging Face 모델
torch              # PyTorch (CPU 버전)
beautifulsoup4     # HTML 파싱
lxml               # XML 생성
python-dotenv      # 환경 변수 관리
pyyaml             # 설정 파일 파싱
```

### 2.3 AI 모델
- **요약**: Facebook BART (Hugging Face Transformers)
  - 모델 크기: ~1.6GB
  - 로컬 실행 (API 키 불필요)
- **번역**: Google Translate via deep-translator
  - 100+ 언어 지원
  - 무료 사용 가능

## 3. GitHub Actions 실행 가능성 검증

### 3.1 리소스 제한 및 해결방안

| 제약사항 | GitHub Actions 제한 | 우리 프로젝트 | 상태 |
|---------|-------------------|--------------|------|
| **실행 시간** | 6시간/작업 | 예상 10-20분 (웹 크롤링 포함) | ✅ 충분 |
| **메모리** | 7GB RAM | BART 모델 ~2GB + 크롤링 | ✅ 충분 |
| **저장 공간** | 14GB | 모델 캐시 ~2GB | ✅ 충분 |
| **월 실행 시간** | 2,000분 (무료) | 3시간마다 × 20분 = 480분/월 | ✅ 충분 |
| **아티팩트** | 500MB/파일 | RSS 파일 < 1MB | ✅ 충분 |
| **네트워크** | 제한 없음 | 30-50개 웹페이지 크롤링 | ✅ 가능 |

### 3.2 모델 캐싱 전략
```yaml
# GitHub Actions 캐시를 활용하여 모델 다운로드 최소화
- uses: actions/cache@v3
  with:
    path: ~/.cache/huggingface
    key: huggingface-models-bart
    # 캐시 유지: 7일 (자동)
```

### 3.3 실행 시간 최적화
- 첫 실행: ~20분 (모델 다운로드 + 웹 크롤링)
- 이후 실행: ~10-15분 (캐시된 모델 사용)
- 아이템 30개 처리 기준 (각 웹페이지 방문 포함)
- 병렬 크롤링으로 시간 단축 가능

## 4. 기능 요구사항

### 4.1 핵심 기능

#### F1: RSS 수집 및 콘텐츠 추출
- Hacker News RSS 피드 주기적 수집
- 각 항목의 링크된 웹페이지 방문 및 본문 추출
- 중복 항목 감지 및 필터링
- 댓글 링크 파싱

#### F2: 웹페이지 콘텐츠 기반 AI 요약
- 각 링크의 실제 웹페이지 내용 추출 (BeautifulSoup)
- 추출된 본문을 2-3문장으로 자동 요약
- 웹페이지 접근 실패시 RSS description 활용
- 기술 용어 및 핵심 정보 보존

#### F3: 다국어 번역
- 제목과 요약 내용 번역
- 다중 언어 동시 지원
- 번역 실패시 영어 원문 유지

#### F4: RSS 생성 및 배포
- 표준 RSS 2.0 형식으로 생성
- 언어별 개별 피드 파일
- GitHub Pages 자동 배포

### 4.2 사용자 설정

```yaml
# config.yaml
general:
  source_feed: "https://news.ycombinator.com/rss"
  update_frequency: "0 */3 * * *"  # 3시간마다
  timezone: "Asia/Seoul"

summarization:
  model: "facebook/bart-large-cnn"
  max_length: 150
  min_length: 50

translation:
  provider: "google"  # google, libre, mymemory
  target_languages:
    - code: "ko"
      name: "Korean"
      feed_name: "rss-ko.xml"
    - code: "ja"
      name: "Japanese"  
      feed_name: "rss-ja.xml"
    - code: "zh-cn"
      name: "Chinese (Simplified)"
      feed_name: "rss-zh.xml"

filtering:
  max_items: 30  # 최대 항목 수 (웹 크롤링 부하 고려)
  max_age_hours: 24  # 24시간 이내 항목만
  skip_jobs: false  # "Ask HN", "Show HN" 포함 여부
  skip_failed_fetches: false  # 콘텐츠 추출 실패 항목 스킵 여부

output:
  base_url: "https://username.github.io/hn-rss-translator"
  keep_days: 7
  generate_index: true
```

## 5. 시스템 아키텍처

### 5.1 처리 플로우

```
1. GitHub Actions Cron Trigger (3시간마다)
   ↓
2. Hacker News RSS 수집
   ↓
3. 캐시 확인 (이미 처리된 항목 스킵)
   ↓
4. 각 링크 방문 및 본문 추출 (requests + BeautifulSoup)
   ↓
5. 추출된 콘텐츠 요약 (BART 모델)
   ↓
6. 각 언어로 번역 (deep-translator)
   ↓
7. RSS XML 생성
   ↓
8. GitHub Pages 배포
```

### 5.2 GitHub Actions 워크플로우

```yaml
name: Update RSS Feeds

on:
  schedule:
    - cron: '0 */3 * * *'
  workflow_dispatch:

jobs:
  update-feeds:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
        cache: 'pip'
    
    - name: Cache Hugging Face models
      uses: actions/cache@v3
      with:
        path: ~/.cache/huggingface
        key: ${{ runner.os }}-huggingface-bart
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run translator
      run: python main.py
    
    - name: Deploy to Pages
      uses: peaceiris/actions-gh-pages@v3
      with:
        github_token: ${{ secrets.GITHUB_TOKEN }}
        publish_dir: ./output
```

## 6. 프로젝트 구조

```
hn-rss-translator/
├── .github/
│   └── workflows/
│       └── update-rss.yml
├── src/
│   ├── __init__.py
│   ├── fetcher.py         # RSS 수집
│   ├── scraper.py         # 웹페이지 콘텐츠 추출
│   ├── summarizer.py      # BART 요약
│   ├── translator.py      # 번역
│   ├── generator.py       # RSS 생성
│   └── utils.py           # 캐싱, 헬퍼 함수
├── cache/
│   └── .gitignore
├── output/
│   └── .gitkeep
├── templates/
│   └── index.html.j2
├── tests/
│   └── test_*.py
├── main.py
├── config.yaml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

## 7. 설치 가이드

### 7.1 빠른 시작

#### Step 1: Fork & Clone
```bash
# GitHub에서 Fork 후
git clone https://github.com/YOUR_USERNAME/hn-rss-translator
cd hn-rss-translator
```

#### Step 2: 설정 수정
```yaml
# config.yaml 편집
translation:
  target_languages:
    - code: "ko"  # 원하는 언어 추가
```

#### Step 3: GitHub 설정
1. **Actions 활성화**
   - Settings → Actions → General
   - Allow all actions and reusable workflows

2. **Pages 활성화**
   - Settings → Pages
   - Source: Deploy from a branch
   - Branch: gh-pages / root

#### Step 4: 첫 실행
- Actions 탭 → "Update RSS Feeds"
- "Run workflow" 클릭

#### Step 5: RSS 구독
```
https://YOUR_USERNAME.github.io/hn-rss-translator/rss-ko.xml
```

### 7.2 로컬 개발

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 실행
python main.py

# 테스트
python -m pytest tests/
```

## 8. 성능 최적화

### 8.1 캐싱 전략
- 번역/요약 결과를 JSON으로 캐싱
- 웹페이지 콘텐츠도 임시 캐싱 (재시도용)
- 7일 이상 오래된 캐시 자동 삭제
- URL 기반 중복 처리 방지

### 8.2 웹 크롤링 최적화
- User-Agent 설정으로 차단 방지
- Timeout 설정 (10초)
- 동시 크롤링 수 제한 (5개)
- 실패한 페이지는 스킵하고 계속 진행

### 8.3 모델 최적화
- CPU 전용 PyTorch 사용
- 경량 모델 옵션 제공 (DistilBART)
- 불필요한 의존성 제거

## 9. 보안 고려사항

### 9.1 API 키 보호
- GitHub Secrets 사용 필수
- 코드에 하드코딩 금지
- `.env` 파일은 `.gitignore`에 포함

### 9.2 Rate Limiting
- API 호출 간 지연 시간 설정
- 실패시 재시도 로직
- 여러 번역 제공자 간 자동 전환

## 10. 기여 가이드

### 10.1 기여 방법
1. Issue 생성 (선택)
2. Fork & Branch 생성
3. 변경사항 커밋
4. Pull Request 생성

### 10.2 개발 규칙
- PEP 8 준수
- 단위 테스트 작성
- 문서화 주석 추가

## 11. 라이센스

MIT License - 자유롭게 사용, 수정, 배포 가능

## 12. 로드맵

### Phase 1: Core MVP
- [ ] Hacker News RSS 수집
- [ ] 웹페이지 콘텐츠 크롤링
- [ ] BART 모델 요약 통합
- [ ] Google Translate 번역
- [ ] RSS 2.0 생성
- [ ] GitHub Actions 자동화
- [ ] GitHub Pages 배포

### Phase 2: 안정화
- [ ] 에러 처리 강화
- [ ] 캐싱 시스템 구현
- [ ] 중복 항목 필터링
- [ ] 실행 로그 개선

### Phase 3: 최적화
- [ ] 배치 처리 구현
- [ ] 메모리 사용 최적화
- [ ] 실행 시간 단축
- [ ] 모델 캐싱 개선

### Phase 4: 사용성 개선
- [ ] 웹 인덱스 페이지
- [ ] 통계 정보 표시
- [ ] 다중 RSS 소스 지원
- [ ] 커스텀 필터 옵션

### Phase 5: 배포
- [ ] 상세 문서 작성
- [ ] 다국어 README
- [ ] Docker 이미지 (선택)
- [ ] 커뮤니티 피드백 반영

---

**오픈소스 프로젝트로 모든 기여를 환영합니다!**
