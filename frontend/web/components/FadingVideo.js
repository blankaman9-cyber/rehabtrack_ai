const FadingVideo = ({ src, className, style }) => {
  const videoRef = React.useRef(null);
  const rafIdRef = React.useRef(null);
  const fadingOutRef = React.useRef(false);

  const fadeTo = (targetOpacity, duration) => {
    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current);
    }
    const startOpacity = parseFloat(videoRef.current?.style.opacity) || 0;
    const startTime = performance.now();

    const animate = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const currentOpacity = startOpacity + (targetOpacity - startOpacity) * progress;
      if (videoRef.current) {
        videoRef.current.style.opacity = currentOpacity.toFixed(4);
      }
      if (progress < 1) {
        rafIdRef.current = requestAnimationFrame(animate);
      }
    };
    rafIdRef.current = requestAnimationFrame(animate);
  };

  React.useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.style.opacity = "0";

    const handleLoadedData = () => {
      video.style.opacity = "0";
      video.play().catch(err => console.log("Play failed:", err));
      fadeTo(1, 500);
    };

    const handleTimeUpdate = () => {
      if (!video.duration) return;
      const timeLeft = video.duration - video.currentTime;
      if (!fadingOutRef.current && timeLeft <= 0.55 && timeLeft > 0) {
        fadingOutRef.current = true;
        fadeTo(0, 500);
      }
    };

    const handleEnded = () => {
      video.style.opacity = "0";
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.currentTime = 0;
          videoRef.current.play().catch(err => console.log("Play failed on loop:", err));
          fadingOutRef.current = false;
          fadeTo(1, 500);
        }
      }, 100);
    };

    video.addEventListener("loadeddata", handleLoadedData);
    video.addEventListener("timeupdate", handleTimeUpdate);
    video.addEventListener("ended", handleEnded);

    if (video.readyState >= 3) {
      handleLoadedData();
    }

    return () => {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
      video.removeEventListener("loadeddata", handleLoadedData);
      video.removeEventListener("timeupdate", handleTimeUpdate);
      video.removeEventListener("ended", handleEnded);
    };
  }, [src]);

  return (
    <video
      ref={videoRef}
      src={src}
      className={className}
      style={style}
      autoPlay
      muted
      playsInline
      preload="auto"
    />
  );
};

window.FadingVideo = FadingVideo;
