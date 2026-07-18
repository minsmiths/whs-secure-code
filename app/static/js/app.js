/* Deuce Market — 인터랙션 (CSP script-src 'self' 준수: 인라인 핸들러 없음) */
(function () {
  "use strict";

  function csrfToken() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute("content") : "";
  }

  /* ---- 찜(하트) 토글 : fetch 로 서버 반영 + 팝 애니메이션 ---- */
  function bindFavorites() {
    document.querySelectorAll("[data-fav-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        var id = btn.getAttribute("data-fav-toggle");

        fetch("/favorites/toggle/" + encodeURIComponent(id), {
          method: "POST",
          headers: {
            "X-CSRFToken": csrfToken(),
            "X-Requested-With": "fetch"
          }
        })
          .then(function (r) {
            if (r.status === 401 || r.redirected) {
              window.location.href = "/auth/login";
              return null;
            }
            return r.ok ? r.json() : null;
          })
          .then(function (data) {
            if (!data) return;
            btn.classList.toggle("on", data.favorited);
            var icon = btn.querySelector("svg");
            if (icon) {
              icon.classList.remove("heart-animate");
              void icon.offsetWidth; // reflow → 애니메이션 재시작
              if (data.favorited) icon.classList.add("heart-animate");
            }
            // 카운트 표시 요소는 버튼 바깥에 있을 수 있어 문서 전체에서 찾는다
            var cnt = document.querySelector("[data-fav-count]");
            if (cnt) cnt.textContent = data.count;
          })
          .catch(function () {});
      });
    });
  }

  /* ---- 이미지 캐러셀 도트 ---- */
  function bindCarousels() {
    document.querySelectorAll("[data-carousel]").forEach(function (car) {
      var track = car.querySelector(".carousel-track");
      var dots = car.querySelectorAll(".carousel-dots .d");
      if (!track || dots.length <= 1) return;
      track.addEventListener("scroll", function () {
        var idx = Math.round(track.scrollLeft / track.clientWidth);
        dots.forEach(function (d, i) { d.classList.toggle("active", i === idx); });
      }, { passive: true });
    });
  }

  /* ---- 삭제 등 확인 다이얼로그 (data-confirm) ---- */
  function bindConfirms() {
    document.querySelectorAll("form[data-confirm]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
      });
    });
  }

  /* ---- flash 자동 사라짐 ---- */
  function bindFlashes() {
    document.querySelectorAll(".flash").forEach(function (el) {
      setTimeout(function () {
        el.style.transition = "opacity .4s, transform .4s";
        el.style.opacity = "0";
        el.style.transform = "translateY(-8px)";
        setTimeout(function () { el.remove(); }, 400);
      }, 2600);
    });
  }

  /* ---- 채팅: 스크롤 맨 아래로 ---- */
  function scrollChat() {
    var s = document.querySelector(".chat-scroll");
    if (s) s.scrollTop = s.scrollHeight;
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindFavorites();
    bindCarousels();
    bindConfirms();
    bindFlashes();
    scrollChat();
  });
})();
