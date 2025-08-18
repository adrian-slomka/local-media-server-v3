function parseSeasonEpisode(text) {
  const match = text.match(/S(\d+)\s*E(\d+)/i);
  if (!match) return { season: 0, episode: 0 };
  return {
    season: parseInt(match[1], 10),
    episode: parseInt(match[2], 10)
  };
}

function sortVideos(sortType) {
  const containers = document.querySelectorAll(".video-panel-container");

  containers.forEach(container => {
    const items = Array.from(container.querySelectorAll("a.video_url"));

    items.sort((a, b) => {
      const videoA = a.querySelector(".media-video");
      const videoB = b.querySelector(".media-video");

      const dateA = new Date(videoA.dataset.date);
      const dateB = new Date(videoB.dataset.date);

      if (dateA.getTime() === dateB.getTime()) {
        // Same date — sort by season and episode from video-text-b
        const textA = a.querySelector(".video-text-b")?.textContent || "";
        const textB = b.querySelector(".video-text-b")?.textContent || "";

        const { season: seasonA, episode: epA } = parseSeasonEpisode(textA);
        const { season: seasonB, episode: epB } = parseSeasonEpisode(textB);

        if (seasonA !== seasonB) {
          return sortType === "newest" ? seasonB - seasonA : seasonA - seasonB;
        }
        return sortType === "newest" ? epB - epA : epA - epB;
      }

      return sortType === "newest" ? dateB - dateA : dateA - dateB;
    });

    items.forEach(item => container.appendChild(item));
  });

  const sortButtons = document.querySelectorAll(".feed-header__sort .media-sort");
  sortButtons.forEach(btn => btn.classList.remove("--sort-active"));
  const activeBtn = document.querySelector(`.feed-header__sort .media-sort[data-sort="${sortType}"]`);
  if (activeBtn) activeBtn.classList.add("--sort-active");
}

document.addEventListener("DOMContentLoaded", () => {
  const sortButtons = document.querySelectorAll(".feed-header__sort .media-sort");

  sortButtons.forEach(button => {
    button.addEventListener("click", () => {
      const sortType = button.dataset.sort;
      sortVideos(sortType);
    });
  });
});