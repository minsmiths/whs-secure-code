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

  /* ---- 채팅 메시지 액션 (공감 / 수정 / 삭제) ---- */
  function post(url, body) {
    return fetch(url, {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken(),
        "X-Requested-With": "fetch",
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: body || ""
    });
  }

  function bindChatActions() {
    // 공감 토글
    document.querySelectorAll("[data-react]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        post("/chat/message/" + btn.getAttribute("data-react") + "/react")
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (d) {
            if (!d) return;
            btn.classList.toggle("on", d.reacted);
            var svg = btn.querySelector("svg");
            if (svg && d.reacted) {
              svg.classList.remove("heart-animate"); void svg.offsetWidth;
              svg.classList.add("heart-animate");
            }
            var c = btn.querySelector("[data-react-count]");
            if (c) c.textContent = d.count > 0 ? d.count : "";
          });
      });
    });

    // 수정
    document.querySelectorAll("[data-edit]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-edit");
        var wrap = btn.closest(".msg");
        var bubble = wrap ? wrap.querySelector("[data-body]") : null;
        if (!bubble) return;
        var cur = bubble.textContent;
        var next = window.prompt("메시지 수정", cur);
        if (next === null) return;
        next = next.trim();
        if (!next || next === cur) return;
        post("/chat/message/" + id + "/edit", "body=" + encodeURIComponent(next))
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (d) {
            if (!d || !d.ok) return;
            bubble.textContent = d.body;
            var t = wrap.querySelector(".time");
            if (t && t.textContent.indexOf("수정됨") === -1) t.textContent = "수정됨 · " + t.textContent;
          });
      });
    });

    // 사진 첨부: 파일 선택 시 폼 자동 전송
    document.querySelectorAll("[data-autosubmit]").forEach(function (input) {
      input.addEventListener("change", function () {
        if (input.files && input.files.length && input.form) input.form.submit();
      });
    });

    // 삭제
    document.querySelectorAll("[data-del]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (!window.confirm("이 메시지를 삭제하시겠습니까?")) return;
        var id = btn.getAttribute("data-del");
        var wrap = btn.closest(".msg");
        post("/chat/message/" + id + "/delete")
          .then(function (r) { return r.ok ? r.json() : null; })
          .then(function (d) {
            if (!d || !d.ok || !wrap) return;
            var col = wrap.querySelector(".msg-col");
            if (col) col.innerHTML = '<div class="bubble deleted">삭제된 메시지입니다</div>';
          });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindFavorites();
    bindCarousels();
    bindConfirms();
    bindFlashes();
    bindChatActions();
    scrollChat();
  });
})();
