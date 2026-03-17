/* =========================================
   햄버거 메뉴 버튼 / 사이드 드로어 요소 가져오기
   ========================================= */
const menuBtn = document.getElementById("menuBtn");
const sideDrawer = document.getElementById("sideDrawer");
const sideDrawerBackdrop = document.getElementById("sideDrawerBackdrop");
const sideDrawerCloseBtn = document.getElementById("sideDrawerCloseBtn");


/* =========================================
   드로어 열기 함수
   ========================================= */
function openDrawer() {
    // hidden 속성을 먼저 해제해서 화면에 보이게 준비
    sideDrawer.hidden = false;
    sideDrawerBackdrop.hidden = false;

    // 다음 렌더링 타이밍에 is-open 클래스 추가
    // 그래야 CSS transition 애니메이션이 자연스럽게 적용됨
    requestAnimationFrame(() => {
        sideDrawer.classList.add("is-open");
        sideDrawerBackdrop.classList.add("is-open");

        // 접근성 속성 변경
        sideDrawer.setAttribute("aria-hidden", "false");

        // body 스크롤 막기
        document.body.classList.add("drawer-open");
    });
}


/* =========================================
   드로어 닫기 함수
   ========================================= */
function closeDrawer() {
    // 열림 상태 클래스 제거
    sideDrawer.classList.remove("is-open");
    sideDrawerBackdrop.classList.remove("is-open");

    // 접근성 속성 변경
    sideDrawer.setAttribute("aria-hidden", "true");

    // body 스크롤 복구
    document.body.classList.remove("drawer-open");

    // 애니메이션이 끝난 뒤 backdrop 숨김
    setTimeout(() => {
        sideDrawerBackdrop.hidden = true;
    }, 240);
}


/* =========================================
   요소가 모두 있을 때만 이벤트 연결
   ========================================= */
if (menuBtn && sideDrawer && sideDrawerBackdrop && sideDrawerCloseBtn) {
    
    // 햄버거 버튼 클릭 -> 드로어 열기
    menuBtn.addEventListener("click", openDrawer);

    // X 버튼 클릭 -> 드로어 닫기
    sideDrawerCloseBtn.addEventListener("click", closeDrawer);

    // 배경 클릭 -> 드로어 닫기
    sideDrawerBackdrop.addEventListener("click", closeDrawer);

    // ESC 키 누르면 드로어 닫기
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && sideDrawer.classList.contains("is-open")) {
            closeDrawer();
        }
    });
}