# 완산제검도관 시합 신청 시스템

## Railway 배포 방법

### 1. GitHub에 올리기
```bash
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/YOUR_ID/kendo-app.git
git push -u origin main
```

### 2. Railway 연결
1. railway.app 접속 → New Project → Deploy from GitHub repo
2. 위에서 만든 레포 선택
3. 자동 배포 시작

### 3. 환경변수 설정 (Railway > Variables)
| 변수명 | 값 | 설명 |
|--------|-----|------|
| `ADMIN_PASSWORD` | 원하는비밀번호 | 관리자 로그인 비밀번호 |
| `SECRET_KEY` | 랜덤문자열 | 세션 암호화 키 |
| `DB_PATH` | `/data/kendo.db` | DB 저장 경로 (Volume 마운트 시) |

### 4. Volume 마운트 (데이터 영구 저장)
Railway > Volumes → Add Volume
- Mount Path: `/data`
- DB_PATH 환경변수를 `/data/kendo.db` 로 설정

## 사용 방법

### 관리자 (사범님/하은)
1. `[배포주소]/admin` 접속
2. 비밀번호로 로그인
3. **대회 세팅 탭**: PDF 업로드하면 자동 파싱 → 저장
4. 링크(`[배포주소]/`) 단톡방에 공유
5. **신청 현황 탭**: 실시간 확인, CSV 다운로드
6. **팀 편성 탭**: AI 팀 구성 제안 받기

### 참가자
1. 단톡방 링크 클릭
2. 이름 / 생년월일 / 단급 / 연락처 입력
3. 개인전 / 단체전 / 둘 다 선택
4. 신청하기 → 완료!
