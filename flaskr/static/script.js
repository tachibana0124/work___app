// 現在時刻を取得して、HTML側に時間表示をしている
function updateClock() {
    const dateEl = document.getElementById('current-date');
    const timeEl = document.getElementById('current-time');

    if (!dateEl || !timeEl) return;

    const now = new Date();

    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');

    const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
    const weekday = weekdays[now.getDay()];

    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');

    dateEl.textContent =
        `${year}年${month}月${day}日 (${weekday})`;

    timeEl.textContent =
        `${hours}:${minutes}:${seconds}`;
}

updateClock();
setInterval(updateClock, 1000);


// LIFF設定、LINE連携の設定
const LIFF_ID = "2012591432-7j0HJLFV";


// LIFF SDKを読み込む
// SDKを使えるようにしている
function loadSdkAndInit() {
    const s = document.createElement('script');

    const host = 'https://' + 'static.' + 'line-scdn.net';
    const path = '/liff/edge/2/sdk.js';

    s.src = host + path;
    s.onload = initializeLiff;

    s.onerror = function() {
        alert("SDKの読み込みに失敗しました");
    };

    document.head.appendChild(s);
}


// LIFFを初期化する
// 読み込んだSDKを使ってLINEと連携する処理
//今回asyncで非同期処理を使えるようにしている
async function initializeLiff() {
    try {
        await liff.init({ liffId: LIFF_ID });

        if (!liff.isLoggedIn()) {
            liff.login();
            return;
        }

        // LINEプロフィールを取得
        const profile = await liff.getProfile();

        // URLのLINEユーザーIDを取得
        const urlParams =
            new URLSearchParams(window.location.search);

        const currentLineId =
            urlParams.get('line_user_id');

        // LINEユーザーIDが一致しなければURLを更新
        if (currentLineId !== profile.userId) {
            window.location.href =
                `/?line_user_id=${encodeURIComponent(profile.userId)}`;
        }

    } catch (error) {
        alert("LIFFエラー: " + error.message);
    }
}


// ページ読み込み完了時にLIFFを起動
window.addEventListener('load', loadSdkAndInit);
