document.addEventListener("DOMContentLoaded", function () {
    var tabList = document.querySelector(".md-tabs__list");
    if (!tabList) return;

    var tabsContainer = document.querySelector(".md-tabs");
    if (!tabsContainer) return;

    // 滚动步长（每次点击滚动的像素数）
    var SCROLL_STEP = 200;

    // 创建左箭头按钮
    var btnLeft = document.createElement("button");
    btnLeft.className = "md-tabs-scroll md-tabs-scroll--left";
    btnLeft.setAttribute("aria-label", "向左滚动");
    btnLeft.innerHTML = "&#9664;";  // ◀

    // 创建右箭头按钮
    var btnRight = document.createElement("button");
    btnRight.className = "md-tabs-scroll md-tabs-scroll--right";
    btnRight.setAttribute("aria-label", "向右滚动");
    btnRight.innerHTML = "&#9654;";  // ▶

    // 注入到 tabs 容器
    tabsContainer.style.position = "relative";
    tabsContainer.appendChild(btnLeft);
    tabsContainer.appendChild(btnRight);

    // 更新箭头可见性
    function updateArrows() {
        var scrollLeft = tabList.scrollLeft;
        var maxScroll = tabList.scrollWidth - tabList.clientWidth;

        // 左箭头：滚动位置 > 0 时显示
        btnLeft.style.display = scrollLeft > 2 ? "flex" : "none";
        // 右箭头：未滚到最右时显示
        btnRight.style.display = scrollLeft < maxScroll - 2 ? "flex" : "none";
    }

    // 点击事件
    btnLeft.addEventListener("click", function () {
        tabList.scrollBy({ left: -SCROLL_STEP, behavior: "smooth" });
    });
    btnRight.addEventListener("click", function () {
        tabList.scrollBy({ left: SCROLL_STEP, behavior: "smooth" });
    });

    // 监听滚动事件更新箭头
    tabList.addEventListener("scroll", updateArrows);
    // 监听窗口缩放
    window.addEventListener("resize", updateArrows);

    // 初始化
    updateArrows();
});
