/************************************************************
 * 전역 상태(State)
 * ----------------------------------------------------------
 * 화면에서 공통으로 사용하는 값들을 한 곳에 모아둔다.
 * 나중에 기능이 늘어나면 여기 상태를 추가하면 된다.
 ************************************************************/
const state = {
    sortBy: "visits",                  // 현재 정렬 기준
    items: [],                        // 현재 화면에 보여주는 음식점 목록
    allItems: [],                     // 전체 음식점 목록 (검색과 무관한 원본 데이터)
    pickedCategory: null,             // 룰렛으로 뽑힌 카테고리
    rouletteAnimating: false,         // 룰렛이 돌고 있는지 여부
    lastRecommendedRestaurantId: null, // 직전에 추천된 음식점 id

    filteredItems: [],
    suggestionItems: [],
    activeSuggestionIndex: -1,
    lastKeyword: "",
    viewMode: "restaurants"
};

window.state = state;

/* 이종민 수정한 부분 */
let naverMap = null;
let naverMarkers = [];
let activeInfoWindow = null;
let activeRestaurantId = null;

/************************************************************
 * DOM 요소 모음
 * ----------------------------------------------------------
 * document.getElementById(...) 를 여기서 한 번만 수행해두면
 * 아래 코드에서 재사용하기 편하다.
 ************************************************************/
const regionSelect = document.getElementById("regionSelect");
const categorySelect = document.getElementById("categorySelect");
const keywordInput = document.getElementById("keywordInput");
const searchBtn = document.getElementById("searchBtn");
const searchSuggestionBox = document.getElementById("searchSuggestionBox");

const restaurantList = document.getElementById("restaurantList");
const mapMarkers = document.getElementById("mapMarkers");
const sortChips = document.querySelectorAll(".sort-chip");

const rouletteBtn = document.getElementById("rouletteBtn");
const rouletteRetryBtn = document.getElementById("rouletteRetryBtn");
const rouletteConfirmBtn = document.getElementById("rouletteConfirmBtn");
const rouletteCloseBtn = document.getElementById("rouletteCloseBtn");
const rouletteResult = document.getElementById("rouletteResult");
const rouletteQuestion = document.getElementById("rouletteQuestion");
const rouletteDesc = document.getElementById("rouletteDesc");
const rouletteSlotTrack = document.getElementById("rouletteSlotTrack");

const mapNotice = document.getElementById("mapNotice");
const mapNoticeToggle = document.getElementById("mapNoticeToggle");

const menuBtn = document.getElementById("menuBtn");
const sideDrawer = document.getElementById("sideDrawer");
const sideDrawerBackdrop = document.getElementById("sideDrawerBackdrop");
const sideDrawerCloseBtn = document.getElementById("sideDrawerCloseBtn");

/* 이종민 수정 3월 12일 2번째 */
const sellerRegisterBtn = document.getElementById("sellerRegisterBtn");

/************************************************************
 * 상수(Constant)
 * ----------------------------------------------------------
 * 코드 안에 숫자를 직접 여러 번 쓰면 나중에 수정하기 어렵다.
 * 의미 있는 숫자는 상수로 빼두는 것이 좋다.
 ************************************************************/
const ROULETTE_ITEM_HEIGHT = 42;
const ROULETTE_MIN_ROUNDS = 5;
const SIDE_DRAWER_CLOSE_DELAY = 280;
const CARD_HIGHLIGHT_DURATION = 1500;
const DEFAULT_IMAGE_URL = "https://placehold.co/300x300?text=No+Image";
const MAX_SUGGESTIONS = 8;

/************************************************************
 * 유틸 함수(작은 도구 함수들)
 ************************************************************/

/**
 * HTML 특수문자를 이스케이프 처리한다.
 * 문자열을 그대로 innerHTML에 넣으면 XSS 같은 문제가 생길 수 있어서
 * 안전하게 바꿔주는 함수다.
 */
function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

/**
 * 숫자처럼 보이는 값을 안전하게 Number로 바꾼다.
 */
function toNumber(value, fallback = 0) {
    const numberValue = Number(value);
    return Number.isNaN(numberValue) ? fallback : numberValue;
}

/**
 * 평점을 항상 소수점 1자리 문자열로 맞춘다.
 */
function formatRating(value) {
    return toNumber(value).toFixed(1);
}

/**
 * 음식점 id로 현재 데이터 또는 전체 데이터에서 음식점을 찾는다.
 */
function findRestaurantById(restaurantId) {
    return (
        state.items.find((item) => Number(item.restaurant_id) === Number(restaurantId)) ||
        state.allItems.find((item) => Number(item.restaurant_id) === Number(restaurantId))
    );
}

/**
 * 로딩 박스를 보여준다.
 */
function showLoading() {
    restaurantList.innerHTML = `<div class="loading-box">음식점 데이터를 불러오는 중...</div>`;
    mapMarkers.innerHTML = "";
}

/**
 * 에러 박스를 보여준다.
 */
function showError() {
    restaurantList.innerHTML = `
        <div class="empty-box">
            데이터를 불러오지 못했습니다.<br />
            DB 연결 및 테이블/컬럼명을 확인해 주세요.
        </div>
    `;
    mapMarkers.innerHTML = "";
}

/**
 * 빈 결과 메시지를 보여준다.
 */
function showEmptyList() {
    restaurantList.innerHTML = `
        <div class="empty-box">
            즐겨찾기에 추가된 음식점이 없습니다.
        </div>
    `;
}

function showLoginRequiredForFavorites() {
    restaurantList.innerHTML = `
        <div class="empty-box">
            로그인 후 이용해 주세요.<br />
            <a href="${window.__INITIAL_STATE__.loginUrl}" class="empty-box-login-link">로그인</a>
        </div>
    `;
    mapMarkers.innerHTML = "";
}

function normalizeText(value) {
    return String(value ?? "")
        .toLowerCase()
        .replace(/\s+/g, "")
        .replace(/[^\wㄱ-ㅎㅏ-ㅣ가-힣]/g, "");
}

function isHangulSyllable(char) {
    const code = char.charCodeAt(0);
    return code >= 0xac00 && code <= 0xd7a3;
}

const CHOSEONG_LIST = [
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"
];

const JUNGSEONG_LIST = [
    "ㅏ", "ㅐ", "ㅑ", "ㅒ", "ㅓ", "ㅔ", "ㅕ", "ㅖ", "ㅗ", "ㅘ",
    "ㅙ", "ㅚ", "ㅛ", "ㅜ", "ㅝ", "ㅞ", "ㅟ", "ㅠ", "ㅡ", "ㅢ", "ㅣ"
];

const JONGSEONG_LIST = [
    "", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ",
    "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"
];

function decomposeHangulToJamo(text) {
    let result = "";

    for (const char of String(text ?? "")) {
        if (!isHangulSyllable(char)) {
            result += char;
            continue;
        }

        const code = char.charCodeAt(0) - 0xac00;
        const choseongIndex = Math.floor(code / 588);
        const jungseongIndex = Math.floor((code % 588) / 28);
        const jongseongIndex = code % 28;

        result += CHOSEONG_LIST[choseongIndex];
        result += JUNGSEONG_LIST[jungseongIndex];
        if (JONGSEONG_LIST[jongseongIndex]) {
            result += JONGSEONG_LIST[jongseongIndex];
        }
    }

    return result;
}

function extractChoseong(text) {
    let result = "";

    for (const char of String(text ?? "")) {
        if (isHangulSyllable(char)) {
            const code = char.charCodeAt(0) - 0xac00;
            const choseongIndex = Math.floor(code / 588);
            result += CHOSEONG_LIST[choseongIndex];
        } else if (/[ㄱ-ㅎ]/.test(char)) {
            result += char;
        }
    }

    return result;
}

function isChoseongOnly(text) {
    const value = String(text ?? "").trim();
    return value.length > 0 && /^[ㄱ-ㅎ]+$/.test(value);
}

function isMixedJamoQuery(text) {
    const value = String(text ?? "").trim();
    if (!value) return false;

    const hasJamo = /[ㄱ-ㅎㅏ-ㅣ]/.test(value);
    const hasSyllable = /[가-힣]/.test(value);

    return hasJamo && hasSyllable;
}

function includesNormalized(text, keyword) {
    return normalizeText(text).includes(normalizeText(keyword));
}

function startsWithNormalized(text, keyword) {
    return normalizeText(text).startsWith(normalizeText(keyword));
}

function includesChoseong(text, keyword) {
    return normalizeText(extractChoseong(text)).includes(normalizeText(keyword));
}

function startsWithChoseong(text, keyword) {
    return normalizeText(extractChoseong(text)).startsWith(normalizeText(keyword));
}

function includesJamo(text, keyword) {
    return normalizeText(decomposeHangulToJamo(text))
        .includes(normalizeText(decomposeHangulToJamo(keyword)));
}

function startsWithJamo(text, keyword) {
    return normalizeText(decomposeHangulToJamo(text))
        .startsWith(normalizeText(decomposeHangulToJamo(keyword)));
}

function getSearchTextBundle(item) {
    const menuText =
        item.menu_names ||
        item.menu_name ||
        item.menus ||
        item.menu ||
        item.signature_menu ||
        "";

    return {
        name: item.name || "",
        region: `${item.region_sido || ""} ${item.region_sigungu || ""}`.trim(),
        category: item.category_name || "",
        menu: Array.isArray(menuText) ? menuText.join(" ") : String(menuText)
    };
}

function matchExactStage(item, keyword) {
    const fields = getSearchTextBundle(item);
    const key = String(keyword ?? "").trim();

    if (!key) return { matched: true, score: 0 };

    let score = 0;

    if (normalizeText(fields.name) === normalizeText(key)) score += 10000;
    else if (startsWithNormalized(fields.name, key)) score += 7000;
    else if (includesNormalized(fields.name, key)) score += 5000;

    if (startsWithNormalized(fields.region, key)) score += 3200;
    else if (includesNormalized(fields.region, key)) score += 2500;

    if (startsWithNormalized(fields.category, key)) score += 2200;
    else if (includesNormalized(fields.category, key)) score += 1700;

    if (startsWithNormalized(fields.menu, key)) score += 1400;
    else if (includesNormalized(fields.menu, key)) score += 1100;

    return { matched: score > 0, score };
}

function matchChoseongStage(item, keyword) {
    const fields = getSearchTextBundle(item);
    const key = String(keyword ?? "").trim();

    if (!isChoseongOnly(key)) return { matched: false, score: 0 };

    let score = 0;

    if (startsWithChoseong(fields.name, key)) score += 6000;
    else if (includesChoseong(fields.name, key)) score += 4500;

    if (startsWithChoseong(fields.region, key)) score += 2800;
    else if (includesChoseong(fields.region, key)) score += 2100;

    if (startsWithChoseong(fields.category, key)) score += 1800;
    else if (includesChoseong(fields.category, key)) score += 1300;

    if (startsWithChoseong(fields.menu, key)) score += 1200;
    else if (includesChoseong(fields.menu, key)) score += 900;

    return { matched: score > 0, score };
}

function matchJamoStage(item, keyword) {
    const fields = getSearchTextBundle(item);
    const key = String(keyword ?? "").trim();

    if (!isMixedJamoQuery(key)) return { matched: false, score: 0 };

    let score = 0;

    if (startsWithJamo(fields.name, key)) score += 5500;
    else if (includesJamo(fields.name, key)) score += 4000;

    if (startsWithJamo(fields.region, key)) score += 2600;
    else if (includesJamo(fields.region, key)) score += 1900;

    if (startsWithJamo(fields.category, key)) score += 1700;
    else if (includesJamo(fields.category, key)) score += 1200;

    if (startsWithJamo(fields.menu, key)) score += 1100;
    else if (includesJamo(fields.menu, key)) score += 800;

    return { matched: score > 0, score };
}

function getTieBreakerScore(item) {
    return (
        toNumber(item.avg_rating) * 10 +
        toNumber(item.review_count) * 0.1 +
        toNumber(item.visit_count) * 0.03
    );
}

function hideSuggestionBox() {
    if (!searchSuggestionBox) return;
    searchSuggestionBox.hidden = true;
    searchSuggestionBox.innerHTML = "";
    state.activeSuggestionIndex = -1;
}

function renderSuggestionList(items, keyword) {
    if (!searchSuggestionBox) return;

    if (!keyword.trim()) {
        hideSuggestionBox();
        return;
    }

    if (!items.length) {
        searchSuggestionBox.hidden = false;
        searchSuggestionBox.innerHTML = `<div class="search-suggestion-empty">추천 검색어가 없습니다.</div>`;
        return;
    }

    searchSuggestionBox.hidden = false;
    searchSuggestionBox.innerHTML = items.map((item, index) => {
        const menuText =
            item.menu_names ||
            item.menu_name ||
            item.menus ||
            item.menu ||
            item.signature_menu ||
            "";

        const menuPreview = Array.isArray(menuText)
            ? menuText.slice(0, 2).join(", ")
            : String(menuText).split(",").slice(0, 2).join(", ");

        const meta = [
            escapeHtml(item.region_sigungu || item.region_sido || ""),
            escapeHtml(item.category_name || "카테고리 미지정"),
            escapeHtml(menuPreview)
        ].filter(Boolean).join(" · ");

        return `
            <button
                type="button"
                class="search-suggestion-item ${index === state.activeSuggestionIndex ? "active" : ""}"
                data-id="${item.restaurant_id}"
                data-index="${index}"
            >
                <span class="search-suggestion-title">${escapeHtml(item.name || "이름 없음")}</span>
                <span class="search-suggestion-meta">${meta}</span>
            </button>
        `;
    }).join("");

    document.querySelectorAll(".search-suggestion-item").forEach((button) => {
        button.addEventListener("mousedown", (event) => {
            event.preventDefault();
        });

        button.addEventListener("click", () => {
            const restaurantId = Number(button.dataset.id);
            const item = findRestaurantById(restaurantId);
            if (!item) return;

            keywordInput.value = item.name || "";
            applyKeywordSearch();
            hideSuggestionBox();
            focusRestaurantCard(item.restaurant_id);
            highlightMarker(item.restaurant_id);
        });
    });
}

function moveSuggestionIndex(direction) {
    if (!state.suggestionItems.length) return;

    if (direction === "down") {
        state.activeSuggestionIndex =
            (state.activeSuggestionIndex + 1) % state.suggestionItems.length;
    } else {
        state.activeSuggestionIndex =
            (state.activeSuggestionIndex - 1 + state.suggestionItems.length) % state.suggestionItems.length;
    }

    renderSuggestionList(state.suggestionItems, keywordInput.value);
}

function selectActiveSuggestion() {
    if (
        state.activeSuggestionIndex < 0 ||
        state.activeSuggestionIndex >= state.suggestionItems.length
    ) {
        applyKeywordSearch();
        return;
    }

    const item = state.suggestionItems[state.activeSuggestionIndex];
    keywordInput.value = item.name || "";
    applyKeywordSearch();
    hideSuggestionBox();
    focusRestaurantCard(item.restaurant_id);
    highlightMarker(item.restaurant_id);
}

function getMatchedEntries(keyword, source) {
    if (!keyword) {
        return source.map((item) => ({
            item,
            matched: true,
            score: 0,
            tie: getTieBreakerScore(item)
        }));
    }

    let matched = source
        .map((item) => {
            const result = matchExactStage(item, keyword);
            return {
                item,
                matched: result.matched,
                score: result.score,
                tie: getTieBreakerScore(item)
            };
        })
        .filter((entry) => entry.matched);

    if (!matched.length) {
        matched = source
            .map((item) => {
                const result = matchChoseongStage(item, keyword);
                return {
                    item,
                    matched: result.matched,
                    score: result.score,
                    tie: getTieBreakerScore(item)
                };
            })
            .filter((entry) => entry.matched);
    }

    if (matched.length < 5) {
        const jamoMatched = source
            .map((item) => {
                const result = matchJamoStage(item, keyword);
                return {
                    item,
                    matched: result.matched,
                    score: result.score,
                    tie: getTieBreakerScore(item)
                };
            })
            .filter((entry) => entry.matched);

        const mergedMap = new Map();

        [...matched, ...jamoMatched].forEach((entry) => {
            const id = Number(entry.item.restaurant_id);
            const prev = mergedMap.get(id);

            if (!prev || entry.score > prev.score) {
                mergedMap.set(id, entry);
            }
        });

        matched = [...mergedMap.values()];
    }

    matched.sort((a, b) => {
        if (b.score !== a.score) return b.score - a.score;
        return b.tie - a.tie;
    });

    return matched;
}

function updateSuggestionsOnly() {
    const keyword = keywordInput?.value.trim() ?? "";
    const source = [...state.items];

    if (!keyword) {
        state.suggestionItems = source.slice(0, MAX_SUGGESTIONS);
        state.activeSuggestionIndex = -1;
        renderSuggestionList(state.suggestionItems, keyword);
        return;
    }

    const matched = getMatchedEntries(keyword, source);

    state.suggestionItems = matched
        .slice(0, MAX_SUGGESTIONS)
        .map((entry) => entry.item);

    state.activeSuggestionIndex = -1;
    renderSuggestionList(state.suggestionItems, keyword);
}

function applyKeywordSearch() {
    const keyword = keywordInput?.value.trim() ?? "";
    const source = [...state.items];

    if (!keyword) {
        state.filteredItems = source;
        renderRestaurantList(state.filteredItems);
        renderMapMarkers(state.filteredItems);

        state.suggestionItems = source.slice(0, MAX_SUGGESTIONS);
        state.activeSuggestionIndex = -1;
        renderSuggestionList(state.suggestionItems, keyword);
        state.lastKeyword = keyword;
        return;
    }

    const matched = getMatchedEntries(keyword, source);

    state.filteredItems = matched.map((entry) => entry.item);

    renderRestaurantList(state.filteredItems);
    renderMapMarkers(state.filteredItems);

    state.suggestionItems = state.filteredItems.slice(0, MAX_SUGGESTIONS);
    state.activeSuggestionIndex = -1;
    renderSuggestionList(state.suggestionItems, keyword);
    state.lastKeyword = keyword;
}

/************************************************************
 * 쿼리 문자열 생성
 ************************************************************/

/**
 * 현재 검색 조건을 이용해 API 쿼리 문자열을 만든다.
 */
function buildFilteredQuery() {
    const params = new URLSearchParams({
        region: regionSelect?.value ?? "",
        category_id: categorySelect?.value ?? "",
        keyword: "",
        sort_by: state.sortBy
    });

    return params.toString();
}

/**
 * 전체 음식점 목록을 가져올 때 사용할 쿼리 문자열을 만든다.
 * 검색 조건 없이 전체 데이터를 가져온다.
 */
function buildAllItemsQuery() {
    const params = new URLSearchParams({
        region: "",
        category_id: "",
        keyword: "",
        sort_by: state.sortBy
    });

    return params.toString();
}

function buildFavoritesQuery() {
    const params = new URLSearchParams({
        region: regionSelect?.value ?? "",
        category_id: categorySelect?.value ?? ""
    });

    return params.toString();
}

/************************************************************
 * 데이터 가져오기
 ************************************************************/

/**
 * 서버에서 데이터를 가져온다.
 * filtered: 현재 검색 조건에 맞는 목록
 * all: 검색과 무관한 전체 목록
 *
 * 두 목록을 동시에 가져오는 이유:
 * - 화면 리스트는 검색 결과를 보여주기 위해
 * - 룰렛은 전체 카테고리와 전체 음식점 기준으로 추천하기 위해
 */
async function fetchRestaurants() {
    showLoading();
    state.viewMode = "restaurants";

    const filteredUrl = `${window.__INITIAL_STATE__.apiUrl}?${buildFilteredQuery()}`;
    const allUrl = `${window.__INITIAL_STATE__.apiUrl}?${buildAllItemsQuery()}`;

    try {
        const [filteredResponse, allResponse] = await Promise.all([
            fetch(filteredUrl),
            fetch(allUrl)
        ]);

        if (!filteredResponse.ok || !allResponse.ok) {
            throw new Error("API 요청 실패");
        }

        const [filteredData, allData] = await Promise.all([
            filteredResponse.json(),
            allResponse.json()
        ]);

        state.items = Array.isArray(filteredData) ? filteredData : [];
        state.allItems = Array.isArray(allData) ? allData : [];

        renderRestaurantList(state.items);
        /* 이종민 추가 3월 12일 - 지도 마커 렌더링 완료 후 검색 결과에 맞게 지도 포커스 */
        await renderMapMarkers(state.items);/*여기*/
        focusMapOnSearchResult(state.items);
        
    } catch (error) {
        console.error(error);
        showError();
    }
}

async function fetchFavoriteRestaurants() {
    showLoading();
    state.viewMode = "favorites";

    const url = `${window.__INITIAL_STATE__.favoritesApiUrl}?${buildFavoritesQuery()}`;

    try {
        const response = await fetch(url);

        if (response.status === 401) {
            showLoginRequiredForFavorites();
            state.items = [];
            state.filteredItems = [];
            return;
        }

        if (!response.ok) {
            throw new Error("즐겨찾기 API 요청 실패");
        }

        const data = await response.json();

        state.items = Array.isArray(data) ? data : [];
        state.filteredItems = [...state.items];

        renderRestaurantList(state.items);
        await renderMapMarkers(state.items);
    } catch (error) {
        console.error(error);
        showError();
    }
}

window.fetchRestaurants = fetchRestaurants;
window.fetchFavoriteRestaurants = fetchFavoriteRestaurants;

/************************************************************
 * 추천 모드 전환
 ************************************************************/

/**
 * 어떤 탭에 있든 "추천" 탭으로 강제로 전환한다.
 * 룰렛은 항상 추천 기준 전체 목록을 보이게 하기 위해 사용한다.
 */
function switchToRecommendMode() {
    state.sortBy = "visits";
    state.viewMode = "restaurants";

    sortChips.forEach((chip) => {
        chip.classList.toggle("active", chip.dataset.sort === "visits");
    });

    state.items = [...state.allItems];
    renderRestaurantList(state.items);
    renderMapMarkers(state.items);
}

/************************************************************
 * 음식점 카드 렌더링
 ************************************************************/

/**
 * 음식점 카드 한 개의 HTML 문자열을 만든다.
 */
function createRestaurantCardHtml(item, index) {
    const title = escapeHtml(item.name || "이름 없음");
    const category = escapeHtml(item.category_name || "카테고리 미지정");
    const region = escapeHtml(item.region_sigungu || item.region_sido || "");
    const description = escapeHtml(item.description || "");
    const address = escapeHtml(item.road_address || item.address || "주소 정보 없음");
    const imageUrl = escapeHtml(item.image_url || DEFAULT_IMAGE_URL);

    const avgRating = formatRating(item.avg_rating);
    const visitCount = toNumber(item.visit_count);
    const reviewCount = toNumber(item.review_count);

    return `
        <article class="restaurant-card" data-id="${item.restaurant_id}">
            <div class="rank-badge">${index + 1}</div>

            <img
                class="card-thumb"
                src="${imageUrl}"
                alt="${title}"
                onerror="this.onerror=null; this.src='${DEFAULT_IMAGE_URL}';"
            />

            <div class="card-body">
                <div class="card-title-row">
                    <h3 class="card-title">${title}</h3>
                    <div class="card-score">★ ${avgRating}</div>
                </div>

                <div class="card-meta">
                    ${category}${region ? ` | ${region}` : ""}
                    ${description ? `<br>${description}` : ""}
                </div>

                <div class="card-address">${address}</div>

                <div class="card-stats">
                    <span class="stat-pill">방문 ${visitCount}</span>
                    <span class="stat-pill">리뷰 ${reviewCount}</span>
                </div>
            </div>
        </article>
    `;
}

/**
 * 음식점 목록 전체를 렌더링한다.
 */
function renderRestaurantList(items) {
    if (!items.length) {
        showEmptyList();
        return;
    }

    restaurantList.innerHTML = items
        .map((item, index) => createRestaurantCardHtml(item, index))
        .join("");

    bindRestaurantCardEvents();
}

/**
 * 카드 클릭 이벤트를 연결한다.
 * 카드 클릭 시 해당 음식점 마커를 강조한다.
 */
function bindRestaurantCardEvents() {
    document.querySelectorAll(".restaurant-card").forEach((card) => {
        card.addEventListener("click", () => {
            const restaurantId = Number(card.dataset.id);
            const item = findRestaurantById(restaurantId);

            if (item) {
                setActiveRestaurantCard(item.restaurant_id);
                highlightMarker(item.restaurant_id);
            }
        });
    });
}

/* 이종민 수정 부분 S*/
function initNaverMap() {
    const mapElement = document.getElementById("naverMap");
    if (!mapElement || !window.naver?.maps) return;

    naverMap = new naver.maps.Map(mapElement, {
        center: new naver.maps.LatLng(37.5665, 126.9780),
        zoom: 14
    });
}

function clearNaverMarkers() {
    naverMarkers.forEach((marker) => marker.setMap(null));
    naverMarkers = [];

    if (activeInfoWindow) {
        activeInfoWindow.close();
        activeInfoWindow = null;
    }
}

function getLatLngFromItem(item) {
    const lat = Number(item.latitude ?? item.lat);
    const lng = Number(item.longitude ?? item.lng);

    if (Number.isFinite(lat) && Number.isFinite(lng)) {
        return new naver.maps.LatLng(lat, lng);
    }

    return null;
}

function createInfoWindowContent(item) {
    const title = escapeHtml(item.name || "이름 없음");
    const category = escapeHtml(item.category_name || "카테고리 미지정");
    const address = escapeHtml(item.road_address || item.address || "주소 정보 없음");
    const rating = formatRating(item.avg_rating);
    const visits = toNumber(item.visit_count);
    const reviews = toNumber(item.review_count);

    return `
        <div style="padding:12px; min-width:220px; line-height:1.5;">
            <strong style="font-size:15px;">${title}</strong><br>
            <span>${category}</span><br>
            <span>${address}</span><br>
            <span>★ ${rating} · 방문 ${visits} · 리뷰 ${reviews}</span>
        </div>
    `;
}

/* 핀 색상 */
function createMarkerIconContent(index) {
    return `
        <div style="
            position: relative;
            width: 34px;
            height: 46px;
            display: flex;
            align-items: flex-start;
            justify-content: center;
        ">
            <div style="
                position: relative;
                width: 34px;
                height: 34px;
                border-radius: 50% 50% 50% 0;
                transform: rotate(-45deg);
                background: linear-gradient(135deg, #8faa7a 0%, #6f8d59 100%);
                border: 2px solid #d7dfb9;
                box-shadow: 0 8px 18px rgba(0, 0, 0, 0.18);
            "></div>

            <span style="
                position: absolute;
                top: 9px;
                left: 50%;
                transform: translateX(-50%);
                font-size: 13px;
                font-weight: 800;
                color: #ffffff;
                line-height: 1;
                z-index: 2;
                pointer-events: none;
            ">${index + 1}</span>
        </div>
    `;
}

function createVisitedMarkerIconContent(index, isActive = false) {
    return `
        <div style="
            position: relative;
            width: 44px;
            height: 52px;
            display: flex;
            align-items: flex-start;
            justify-content: center;
        ">
            <div style="
                width: 40px;
                height: 40px;
                background-image: url('/static/img/stamp.png');
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
                filter: ${isActive
                    ? "drop-shadow(0 8px 18px rgba(0,0,0,0.28))"
                    : "drop-shadow(0 6px 12px rgba(0,0,0,0.18))"};
            "></div>

            <span style="
                position: absolute;
                left: 0;
                top: -2px;
                min-width: 18px;
                height: 18px;
                padding: 0px 0px 0px 0px;
                border-radius: 999px;
                background: #ffffff;
                color: #b22222;
                font-size: 12px;
                font-weight: 800;
                line-height: 18px;
                text-align: center;
                z-index: 3;
                box-shadow: 0 2px 8px rgba(0,0,0,0.18);
            ">${index + 1}</span>
        </div>
    `;
}

function geocodeAddress(address) {
    return Promise.resolve(null);
}

/**
 * 지도에 마커를 그린다.
 * 현재는 상위 10개만 표시한다.
 */

/* 이종민 추가 3월 12일 - 검색 시 첫 번째 결과 매장으로 지도 이동 */
function focusMapOnSearchResult(items) {
    if (!naverMap || !Array.isArray(items) || items.length === 0) return;

    const keyword = (keywordInput?.value || "").trim();
    const selectedRegion = regionSelect?.value || "";
    const selectedCategory = categorySelect?.value || "";

    const hasSearchCondition =
        keyword.length > 0 ||
        (selectedRegion && selectedRegion !== "전체") ||
        selectedCategory.length > 0;

    if (!hasSearchCondition) {
        return;
    }

    const targetItem = items[0];
    if (!targetItem) return;

    requestAnimationFrame(() => {
        highlightMarker(targetItem.restaurant_id);
    });
}
/* 이종민 수정 부분 E*/

/************************************************************
 * 룰렛 결과 표시
 ************************************************************/

/**
 * 최종 추천된 음식점 정보를 룰렛 박스에 표시한다.
 */
function renderRecommendedResult(item) {
    const category = item.category_name || "카테고리 미지정";
    const region = item.region_sigungu || item.region_sido || "지역 정보 없음";
    const rating = formatRating(item.avg_rating);
    const visits = toNumber(item.visit_count);

    rouletteSlotTrack.innerHTML = `
        <div class="roulette-slot__item">${escapeHtml(item.name || "이름 없음")}</div>
    `;
    rouletteSlotTrack.style.transition = "none";
    rouletteSlotTrack.style.transform = "translateY(0)";

    rouletteQuestion.textContent = `${category} · ${region} · ★ ${rating} · 방문 ${visits}`;
    rouletteDesc.textContent = "이 음식점을 오늘의 추천으로 골라봤어요.";
}

/************************************************************
 * 카드 포커스 / 하이라이트
 ************************************************************/

/**
 * 특정 음식점 카드를 화면 중앙으로 스크롤하고 잠깐 강조한다.
 */
function focusRestaurantCard(restaurantId) {
    const targetCard = document.querySelector(`.restaurant-card[data-id="${restaurantId}"]`);
    const list = document.getElementById("restaurantList");
    if (!targetCard || !list) return;

    setActiveRestaurantCard(restaurantId);

    const listRect = list.getBoundingClientRect();
    const cardRect = targetCard.getBoundingClientRect();

    const isAbove = cardRect.top < listRect.top;
    const isBelow = cardRect.bottom > listRect.bottom;

    if (isAbove || isBelow) {
        const offset = targetCard.offsetTop - list.clientHeight / 2 + targetCard.clientHeight / 2;
        list.scrollTo({
            top: offset,
            behavior: "smooth"
        });
    }

    targetCard.style.boxShadow =
        "0 0 0 3px rgba(143, 170, 122, 0.25), 0 10px 30px rgba(0, 0, 0, 0.06)";

    setTimeout(() => {
        targetCard.style.boxShadow = "";
    }, CARD_HIGHLIGHT_DURATION);
}

function setActiveRestaurantCard(restaurantId) {
    document.querySelectorAll(".restaurant-card").forEach((card) => {
        card.classList.toggle(
            "is-active",
            Number(card.dataset.id) === Number(restaurantId)
        );
    });

    activeRestaurantId = Number(restaurantId);
}

/**
 * 전체 음식점 목록을 보여주고, 특정 음식점에 포커스를 준다.
 */
function showAllRestaurantsAndFocus(item) {
    switchToRecommendMode();
    highlightMarker(item.restaurant_id);

    requestAnimationFrame(() => {
        focusRestaurantCard(item.restaurant_id);
    });
}

/************************************************************
 * 룰렛 관련 함수
 ************************************************************/

/**
 * 현재 룰렛 버튼/확인/다시뽑기 버튼 상태를 한 번에 바꾼다.
 */
function setRouletteButtonsDisabled(disabled) {
    if (rouletteConfirmBtn) rouletteConfirmBtn.disabled = disabled;
    if (rouletteRetryBtn) rouletteRetryBtn.disabled = disabled;
    if (rouletteBtn) rouletteBtn.disabled = disabled;
}

/**
 * 룰렛 박스를 초기 상태로 되돌린다.
 */
function resetRouletteBox() {
    rouletteSlotTrack.innerHTML = `<div class="roulette-slot__item">한식</div>`;
    rouletteSlotTrack.style.transition = "none";
    rouletteSlotTrack.style.transform = "translateY(0)";

    rouletteQuestion.textContent = "이 카테고리 음식점을 추천해드릴까요?";
    rouletteDesc.textContent = "주사위를 다시 눌러도 다른 카테고리를 추천받을 수 있어요.";
}

/**
 * 전체 음식점 목록에서 중복 없는 카테고리 배열을 만든다.
 */
function getAllCategories() {
    return [...new Set(
        state.allItems
            .map((item) => item.category_name)
            .filter(Boolean)
    )];
}

/**
 * 룰렛 애니메이션에 사용할 카테고리 시퀀스를 만든다.
 * 예:
 * [한식, 일식, 중식, ...] 를 여러 번 반복하고,
 * 마지막에는 실제 당첨 카테고리에서 멈추도록 구성한다.
 */
function buildRouletteSpinSequence(categories, finalIndex) {
    const spinSequence = [];

    for (let round = 0; round < ROULETTE_MIN_ROUNDS; round += 1) {
        spinSequence.push(...categories);
    }

    for (let i = 0; i <= finalIndex; i += 1) {
        spinSequence.push(categories[i]);
    }

    return spinSequence;
}

/**
 * 룰렛 박스를 닫는다.
 */
function closeRouletteBox() {
    rouletteResult.hidden = true;
    state.pickedCategory = null;
    state.rouletteAnimating = false;

    resetRouletteBox();
    setRouletteButtonsDisabled(false);
}

/**
 * 룰렛으로 뽑힌 카테고리에서 음식점을 랜덤 추천한다.
 *
 * 규칙:
 * - 같은 카테고리 식당이 여러 개 있으면 직전 추천 식당은 제외
 * - 같은 카테고리 식당이 1개뿐이면 그대로 추천
 */
function recommendRestaurantFromPickedCategory() {
    if (state.rouletteAnimating) return;

    if (!state.pickedCategory) {
        alert("먼저 카테고리를 뽑아주세요.");
        return;
    }

    const sameCategoryItems = state.allItems.filter(
        (item) => item.category_name === state.pickedCategory
    );

    if (!sameCategoryItems.length) {
        alert("해당 카테고리의 음식점이 없습니다.");
        return;
    }

    let candidateItems = sameCategoryItems;

    if (sameCategoryItems.length > 1 && state.lastRecommendedRestaurantId !== null) {
        const filteredItems = sameCategoryItems.filter(
            (item) => Number(item.restaurant_id) !== Number(state.lastRecommendedRestaurantId)
        );

        if (filteredItems.length) {
            candidateItems = filteredItems;
        }
    }

    const randomIndex = Math.floor(Math.random() * candidateItems.length);
    const pickedRestaurant = candidateItems[randomIndex];

    state.lastRecommendedRestaurantId = pickedRestaurant.restaurant_id;

    renderRecommendedResult(pickedRestaurant);
    showAllRestaurantsAndFocus(pickedRestaurant);
}

/**
 * 룰렛을 돌려서 카테고리를 하나 뽑는다.
 */
function pickRandomCategory() {
    if (!state.allItems.length) {
        alert("추천할 음식점 데이터가 없습니다.");
        return;
    }

    if (state.rouletteAnimating) return;

    // 룰렛 시작 시 무조건 추천 모드로 전환
    switchToRecommendMode();

    const categories = getAllCategories();

    if (!categories.length) {
        alert("카테고리 정보가 없습니다.");
        return;
    }

    state.rouletteAnimating = true;
    state.pickedCategory = null;
    rouletteResult.hidden = false;

    rouletteQuestion.textContent = "카테고리를 고르는 중..";
    rouletteDesc.textContent = "뭐 먹을지 찾는 중..";
    setRouletteButtonsDisabled(true);

    const finalIndex = Math.floor(Math.random() * categories.length);
    const finalCategory = categories[finalIndex];
    const spinSequence = buildRouletteSpinSequence(categories, finalIndex);

    rouletteSlotTrack.innerHTML = spinSequence
        .map((category) => `<div class="roulette-slot__item">${escapeHtml(category)}</div>`)
        .join("");

    // 애니메이션 시작 전 초기 위치 세팅
    rouletteSlotTrack.style.transition = "none";
    rouletteSlotTrack.style.transform = "translateY(0)";

    // 강제 리플로우: 브라우저가 현재 상태를 먼저 반영하도록 함
    void rouletteSlotTrack.offsetHeight;

    let step = 0;
    const lastStep = spinSequence.length - 1;

    function moveNext() {
        step += 1;
        rouletteSlotTrack.style.transform = `translateY(-${step * ROULETTE_ITEM_HEIGHT}px)`;

        if (step < lastStep) {
            const progress = step / lastStep;
            const delay = 40 + Math.pow(progress, 2.2) * 100;

            setTimeout(() => {
                rouletteSlotTrack.style.transition = "transform 0.09s linear";
                moveNext();
            }, delay);
        } else {
            state.pickedCategory = finalCategory;
            state.rouletteAnimating = false;

            rouletteQuestion.textContent = "이 카테고리 음식점을 추천해드릴까요?";
            rouletteDesc.textContent = "확인을 누르면 해당 카테고리의 음식점 중 한 곳을 추천해드려요.";
            setRouletteButtonsDisabled(false);
        }
    }

    requestAnimationFrame(() => {
        rouletteSlotTrack.style.transition = "transform 0.09s linear";
        setTimeout(moveNext, 80);
    });
}

/************************************************************
 * 지도 마커 렌더링
 ************************************************************/

/* 민규동 수정 0313 - DB 위도/경도만 사용해서 지도 마커 표시 */
async function renderMapMarkers(items) {
    if (!naverMap) return;

    clearNaverMarkers();

    if (!items.length) {
        return;
    }

    const bounds = new naver.maps.LatLngBounds();
    let hasMarker = false; // 이종민 추가 3월 12일 - 실제 마커 생성 여부 확인

    /* 이종민 수정 3월 12일 - 검색 결과 전체를 지도에 표시 */
    items.forEach((item, index) => {
        const position = getLatLngFromItem(item);

        if (!position) return;

        hasMarker = true;

        const isVisited = Boolean(item.has_visited);

        const marker = new naver.maps.Marker({
            position: position,
            map: naverMap,
            title: item.name || "이름 없음",
            icon: {
                content: isVisited
                    ? createVisitedMarkerIconContent(index, false)
                    : createMarkerIconContent(index),
                size: isVisited
                    ? new naver.maps.Size(44, 52)
                    : new naver.maps.Size(34, 46),
                anchor: isVisited
                    ? new naver.maps.Point(22, 52)
                    : new naver.maps.Point(17, 46)
            }
        });

        marker.restaurantId = Number(item.restaurant_id);
        marker.markerIndex = index;
        marker.isVisited = isVisited;

        naver.maps.Event.addListener(marker, "click", () => {

            highlightMarker(item.restaurant_id);

            focusRestaurantCard(item.restaurant_id);

            setTimeout(() => {
                openDetailPanel(item.restaurant_id);
            }, 0);
        });

        naverMarkers.push(marker);
        bounds.extend(position);
    });

    /* 이종민 수정 3월 12일 - bounds.isEmpty() 대신 실제 마커 존재 여부로 판단 */
    /* 이종민 수정 3월 12일 - bounds에 맞춘 뒤 한 단계 더 축소해서 조금 멀리서 보이게 */
    if (hasMarker) {
        /* 이종민 수정 3월 12일 - 줌 단계 조절 대신 fitBounds 여백으로 미세 조정 */
        naverMap.fitBounds(bounds, {
            top: 40,
            right: 40,
            bottom: 40,
            left: 40,
            maxZoom: 16
        });
    }
}

/**
 * 마커 클릭 이벤트를 연결한다.
 */
function bindMapMarkerEvents() {
    document.querySelectorAll(".map-marker").forEach((marker) => {
        marker.addEventListener("click", () => {
            const restaurantId = Number(marker.dataset.id);
            const item = findRestaurantById(restaurantId);

            if (!item) return;

            highlightMarker(restaurantId);
        });
    });
}

/**
 * 특정 음식점 마커를 강조한다.
 */
/* 민규동 수정 3월 13일 */
function highlightMarker(restaurantId) {
    const targetMarker = naverMarkers.find(
        (marker) => Number(marker.restaurantId) === Number(restaurantId)
    );

    if (!targetMarker || !naverMap) return;

    naverMarkers.forEach((marker) => {
        const isActive = Number(marker.restaurantId) === Number(restaurantId);
        const isVisited = Boolean(marker.isVisited);

        marker.setIcon({
            content: isVisited
                ? createVisitedMarkerIconContent(marker.markerIndex, isActive)
                : `
                    <div style="
                        position: relative;
                        width: 34px;
                        height: 46px;
                        display: flex;
                        align-items: flex-start;
                        justify-content: center;
                    ">
                        <div style="
                            position: relative;
                            width: 34px;
                            height: 34px;
                            border-radius: 50% 50% 50% 0;
                            transform: rotate(-45deg);
                            background: linear-gradient(
                                135deg,
                                ${isActive ? "#6f8d59" : "#8faa7a"} 0%,
                                ${isActive ? "#4f6d3e" : "#6f8d59"} 100%
                            );
                            border: 2px solid #d7dfb9;
                            box-shadow: ${isActive
                                ? "0 10px 24px rgba(111, 141, 89, 0.38)"
                                : "0 8px 18px rgba(0, 0, 0, 0.18)"};
                        "></div>

                        <span style="
                            position: absolute;
                            top: 9px;
                            left: 50%;
                            transform: translateX(-50%);
                            font-size: ${isActive ? 14 : 13}px;
                            font-weight: 800;
                            color: #ffffff;
                            line-height: 1;
                            z-index: 2;
                            pointer-events: none;
                        ">${marker.markerIndex + 1}</span>
                    </div>
                `,
            size: isVisited
                ? new naver.maps.Size(44, 52)
                : new naver.maps.Size(34, 46),
            anchor: isVisited
                ? new naver.maps.Point(22, 52)
                : new naver.maps.Point(17, 46)
        });

        marker.setZIndex(isActive ? 200 : 100);
    });

    const position = targetMarker.getPosition();
    if (position) {
        naverMap.panTo(position);
    }
}

/************************************************************
 * 우측 드로어(햄버거 메뉴)
 ************************************************************/

/**
 * 우측 드로어를 연다.
 */
function openSideDrawer() {
    if (!sideDrawer || !sideDrawerBackdrop) return;

    sideDrawer.hidden = false;
    sideDrawerBackdrop.hidden = false;

    requestAnimationFrame(() => {
        sideDrawer.classList.add("is-open");
        sideDrawerBackdrop.classList.add("is-open");
        sideDrawer.setAttribute("aria-hidden", "false");
        document.body.classList.add("drawer-open");
    });
}

/**
 * 우측 드로어를 닫는다.
 */
function closeSideDrawer() {
    if (!sideDrawer || !sideDrawerBackdrop) return;

    sideDrawer.classList.remove("is-open");
    sideDrawerBackdrop.classList.remove("is-open");
    sideDrawer.setAttribute("aria-hidden", "true");
    document.body.classList.remove("drawer-open");

    setTimeout(() => {
        sideDrawer.hidden = true;
        sideDrawerBackdrop.hidden = true;
    }, SIDE_DRAWER_CLOSE_DELAY);
}

/************************************************************
 * 이벤트 연결
 ************************************************************/

/**
 * 정렬 칩 이벤트 연결
 */
function bindSortChipEvents() {
    sortChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            sortChips.forEach((targetChip) => targetChip.classList.remove("active"));
            chip.classList.add("active");

            state.sortBy = chip.dataset.sort;

            if (chip.dataset.sort === "latest") {
                fetchFavoriteRestaurants();
                return;
            }

            fetchRestaurants();
        });
    });
}

/**
 * 검색 관련 이벤트 연결
 */
function bindSearchEvents() {
    if (searchBtn) {
        searchBtn.addEventListener("click", () => {
            applyKeywordSearch();
        });
    }

    if (keywordInput) {
        keywordInput.addEventListener("input", () => {
            updateSuggestionsOnly();
        });

        keywordInput.addEventListener("focus", () => {
            if (keywordInput.value.trim()) {
                renderSuggestionList(state.suggestionItems, keywordInput.value);
            }
        });

        keywordInput.addEventListener("keydown", (event) => {
            if (event.key === "ArrowDown") {
                event.preventDefault();
                moveSuggestionIndex("down");
                return;
            }

            if (event.key === "ArrowUp") {
                event.preventDefault();
                moveSuggestionIndex("up");
                return;
            }

            if (event.key === "Enter") {
                event.preventDefault();
                selectActiveSuggestion();
                return;
            }

            if (event.key === "Escape") {
                hideSuggestionBox();
            }
        });
    }

    if (regionSelect) {
        regionSelect.addEventListener("change", () => {
            if (state.viewMode === "favorites") {
                fetchFavoriteRestaurants();
                return;
            }
            fetchRestaurants();
        });
    }

    if (categorySelect) {
        categorySelect.addEventListener("change", () => {
            if (state.viewMode === "favorites") {
                fetchFavoriteRestaurants();
                return;
            }
            fetchRestaurants();
        });
    }

    document.addEventListener("click", (event) => {
        const target = event.target;

        if (
            target === keywordInput ||
            target.closest(".search-suggestion-box") ||
            target.closest(".search-input-wrap")
        ) {
            return;
        }

        hideSuggestionBox();
    });
}

/**
 * 룰렛 관련 이벤트 연결
 */
function bindRouletteEvents() {
    if (rouletteBtn) {
        rouletteBtn.addEventListener("click", pickRandomCategory);
    }

    if (rouletteRetryBtn) {
        rouletteRetryBtn.addEventListener("click", pickRandomCategory);
    }

    if (rouletteConfirmBtn) {
        rouletteConfirmBtn.addEventListener("click", recommendRestaurantFromPickedCategory);
    }

    if (rouletteCloseBtn) {
        rouletteCloseBtn.addEventListener("click", closeRouletteBox);
    }
}

/**
 * 공지사항 토글 이벤트 연결
 */
function bindMapNoticeEvents() {
    if (!mapNotice || !mapNoticeToggle) return;

    mapNoticeToggle.addEventListener("click", () => {
        const isCollapsed = mapNotice.classList.toggle("collapsed");

        if (isCollapsed) {
            mapNoticeToggle.setAttribute("aria-label", "공지사항 펼치기");
            mapNoticeToggle.setAttribute("aria-expanded", "false");
        } else {
            mapNoticeToggle.setAttribute("aria-label", "공지사항 접기");
            mapNoticeToggle.setAttribute("aria-expanded", "true");
        }
    });
}

/**
 * 사이드 드로어 이벤트 연결
 */
function bindSideDrawerEvents() {
    if (menuBtn) {
        menuBtn.addEventListener("click", openSideDrawer);
        if (sellerRegisterBtn) {
            sellerRegisterBtn.addEventListener("click", () => {
                closeSideDrawer();
                window.location.href = "/seller/register";
            });
        }
    
    }

    if (sideDrawerCloseBtn) {
        sideDrawerCloseBtn.addEventListener("click", closeSideDrawer);
    }

    if (sideDrawerBackdrop) {
        sideDrawerBackdrop.addEventListener("click", closeSideDrawer);
    }

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeSideDrawer();
        }
    });
}

/************************************************************
 * 초기 실행
 ************************************************************/

/**
 * 페이지가 처음 열릴 때 실행되는 함수
 * - 이벤트 연결
 * - 첫 데이터 로드
 */
function init() {
    initNaverMap();
    bindSortChipEvents();
    bindSearchEvents();
    bindRouletteEvents();
    bindMapNoticeEvents();
    bindSideDrawerEvents();
    fetchRestaurants();
}

init();

const profileToggle = document.getElementById("profileToggle");
const profileDropdown = document.getElementById("profileDropdown");

if (profileToggle && profileDropdown) {
    profileToggle.addEventListener("click", function (e) {
        e.stopPropagation();
        profileDropdown.classList.toggle("show");
    });

    document.addEventListener("click", function (e) {
        if (!profileToggle.contains(e.target) && !profileDropdown.contains(e.target)) {
            profileDropdown.classList.remove("show");
        }
    });
}