// Joint angle definitions
const ANGLE_TRIPLETS = [
  [13, 11, 23], // 0  Left shoulder
  [14, 12, 24], // 1  Right shoulder
  [11, 13, 15], // 2  Left elbow
  [12, 14, 16], // 3  Right elbow
  [13, 15, 11], // 4  Left wrist flex
  [14, 16, 12], // 5  Right wrist flex
  [11, 23, 25], // 6  Left hip
  [12, 24, 26], // 7  Right hip
  [11, 23, 24], // 8  Left lateral trunk tilt
  [12, 24, 23], // 9  Right lateral trunk tilt
  [23, 25, 27], // 10 Left knee
  [24, 26, 28], // 11 Right knee
  [25, 27, 29], // 12 Left ankle
  [26, 28, 30], // 13 Right ankle
  [11, 12, 24], // 14 Shoulder–hip cross (right side)
  [12, 11, 23]  // 15 Shoulder–hip cross (left side)
];

const POSE_CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 7],
  [0, 4], [4, 5], [5, 6], [6, 8],
  [9, 10],
  [11, 12], [11, 13], [13, 15], [15, 17], [15, 19], [15, 21],
  [12, 14], [14, 16], [16, 18], [16, 20], [16, 22],
  [11, 23], [12, 24], [23, 24],
  [23, 25], [25, 27], [27, 29], [27, 31], [29, 31],
  [24, 26], [26, 28], [28, 30], [28, 32], [30, 32]
];

const EXERCISE_LABELS = ["Squat", "Arm Cross", "Body Twist", "Step Jack"];

// Primary joint angle index used for rep detection per exercise
const EXERCISE_PRIMARY_ANGLE = {
  "Squat":      10,  // Left knee
  "Arm Cross":   0,  // Left shoulder
  "Body Twist":  8,  // Left lateral trunk tilt
  "Step Jack":   6,  // Left hip
};
const MIN_REP_ANGLE_CHANGE = 25; // Minimum degrees of motion to qualify as a rep phase

// Custom SVG Line Chart
const LineChart = ({ data, color = "#ffffff", height = 140 }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-white/40 text-xs italic" style={{ height }}>
        Awaiting movement data...
      </div>
    );
  }

  const minVal = 0;
  const maxVal = 180;
  const range = maxVal - minVal;

  const points = data.map((val, i) => {
    const x = (i / (data.length - 1 || 1)) * 100;
    const y = 100 - ((val - minVal) / range) * 100;
    return `${x},${y}`;
  }).join(" ");

  return (
    <div className="w-full relative py-2" style={{ height }}>
      <svg className="w-full h-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
        <line x1="0" y1="25" x2="100" y2="25" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />
        <line x1="0" y1="50" x2="100" y2="50" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />
        <line x1="0" y1="75" x2="100" y2="75" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />
        
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          points={points}
          style={{ filter: "drop-shadow(0px 0px 4px rgba(255,255,255,0.3))" }}
        />
      </svg>
      <div className="absolute top-0 left-0 text-[9px] text-white/30">{maxVal}°</div>
      <div className="absolute bottom-0 left-0 text-[9px] text-white/30">{minVal}°</div>
      <div className="absolute bottom-0 right-0 text-[9px] text-white/50">Angle: {Math.round(data[data.length - 1])}°</div>
    </div>
  );
};

// Custom Horizontal Bar Chart
const BarChart = ({ data, color = "#ffffff" }) => {
  return (
    <div className="flex flex-col gap-2.5 py-1 w-full">
      {Object.entries(data).map(([label, val]) => (
        <div key={label} className="w-full">
          <div className="flex justify-between text-[11px] mb-1 text-white/70">
            <span>{label}</span>
            <span>{val.toFixed(1)}%</span>
          </div>
          <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden relative">
            <div
              className="h-full rounded-full transition-all duration-150"
              style={{
                width: `${val}%`,
                backgroundColor: color,
                boxShadow: `0 0 6px ${color}`
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
};

function angleBetween(a, vertex, b) {
  const v1 = { x: a.x - vertex.x, y: a.y - vertex.y, z: a.z - vertex.z };
  const v2 = { x: b.x - vertex.x, y: b.y - vertex.y, z: b.z - vertex.z };

  const norm1 = Math.sqrt(v1.x * v1.x + v1.y * v1.y + v1.z * v1.z);
  const norm2 = Math.sqrt(v2.x * v2.x + v2.y * v2.y + v2.z * v2.z);

  if (norm1 < 1e-6 || norm2 < 1e-6) return 0.0;

  const dot = v1.x * v2.x + v1.y * v2.y + v1.z * v2.z;
  let cosTheta = dot / (norm1 * norm2);
  cosTheta = Math.max(-1.0, Math.min(1.0, cosTheta));
  return (Math.acos(cosTheta) * 180.0) / Math.PI;
}

function computeAngles(landmarks) {
  return ANGLE_TRIPLETS.map(([a, v, b]) =>
    angleBetween(landmarks[a], landmarks[v], landmarks[b])
  );
}

const PatientDashboard = ({ user }) => {
  const [patients, setPatients] = React.useState([]);
  const [selectedPatientId, setSelectedPatientId] = React.useState(user ? user.id : 1);
  const [patient, setPatient] = React.useState(null);
  const [prescriptions, setPrescriptions] = React.useState([]);
  const [selectedPresc, setSelectedPresc] = React.useState(null);

  // Live session states
  const [trackingActive, setTrackingActive] = React.useState(false);
  const trackingActiveRef = React.useRef(false);
  const [paused, setPaused] = React.useState(false);
  const pausedRef = React.useRef(false);
  const [reps, setReps] = React.useState(0);
  const repsRef = React.useRef(0);
  const [avgScore, setAvgScore] = React.useState(0);
  const [currentScore, setCurrentScore] = React.useState(0);
  const [currentLabel, setCurrentLabel] = React.useState("—");
  const [bufferFill, setBufferFill] = React.useState(0);

  // History lists for charts
  const [angleHistory, setAngleHistory] = React.useState([]);
  const [probHistory, setProbHistory] = React.useState({
    "Squat": 0, "Arm Cross": 0, "Body Twist": 0, "Step Jack": 0
  });

  const [notification, setNotification] = React.useState(null);

  // References for live media loop
  const videoRef = React.useRef(null);
  const canvasRef = React.useRef(null);
  const streamRef = React.useRef(null);
  const landmarkerRef = React.useRef(null);
  const animFrameIdRef = React.useRef(null);
  
  // Data buffer refs
  const bufferRef = React.useRef([]);
  const scoreHistoryRef = React.useRef([]);
  const romHistoryRef = React.useRef([]);
  const labelHistoryRef = React.useRef([]);
  const apiStrideCounterRef = React.useRef(0);
  const isDemoModeRef = React.useRef(false);
  const demoTimeRef = React.useRef(0);
  const demoTimeoutRef = React.useRef(null);

  // Angle-based rep detection state machine
  const REP_COOLDOWN_MS = 4000;
  const lastRepTimeRef = React.useRef(0);
  const cooldownIntervalRef = React.useRef(null);
  const [repCooldown, setRepCooldown] = React.useState(0); // seconds remaining
  const currentLabelRef = React.useRef("\u2014");
  const repPhaseRef = React.useRef("READY");     // "READY" or "CONTRACTED"
  const runningPeakRef = React.useRef(0);
  const runningValleyRef = React.useRef(180);

  // Fetch Patients on Load
  React.useEffect(() => {
    fetch("/api/patients")
      .then(res => res.json())
      .then(data => {
        setPatients(data);
        if (!user && data.length > 0) {
          setSelectedPatientId(data[0].id);
        }
      })
      .catch(err => console.error("Error fetching patients:", err));
  }, [user]);

  React.useEffect(() => {
    if (user) {
      setSelectedPatientId(user.id);
    }
  }, [user]);

  // Fetch Patient profile details & active prescriptions
  React.useEffect(() => {
    if (!selectedPatientId) return;
    fetch(`/api/patients/${selectedPatientId}`)
      .then(res => res.json())
      .then(data => setPatient(data))
      .catch(err => console.error(err));

    fetch(`/api/prescriptions/${selectedPatientId}`)
      .then(res => res.json())
      .then(data => {
        setPrescriptions(data);
        setSelectedPresc(data.length > 0 ? data[0] : null);
      })
      .catch(err => console.error(err));
  }, [selectedPatientId]);

  // Load MediaPipe Model on Mount (with retry for async ES module loading)
  React.useEffect(() => {
    let cancelled = false;
    let retryCount = 0;
    const MAX_RETRIES = 20;
    const RETRY_INTERVAL = 500; // ms

    async function loadModel() {
      try {
        if (!window.FilesetResolver || !window.PoseLandmarker) {
          if (retryCount < MAX_RETRIES) {
            retryCount++;
            console.log(`MediaPipe scripts loading... (retry ${retryCount}/${MAX_RETRIES})`);
            setTimeout(() => { if (!cancelled) loadModel(); }, RETRY_INTERVAL);
          } else {
            console.error("MediaPipe scripts failed to load after maximum retries.");
          }
          return;
        }
        const vision = await window.FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.8/wasm"
        );
        landmarkerRef.current = await window.PoseLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "/pose_landmarker.task",
            delegate: "GPU"
          },
          runningMode: "VIDEO",
          numPoses: 1
        });
        console.log("[MediaPipe] Pose Landmarker Loaded.");
      } catch (err) {
        console.error("Failed to load MediaPipe PoseLandmarker:", err);
      }
    }
    loadModel();

    return () => {
      cancelled = true;
      stopSession();
    };
  }, []);

  const startSession = async () => {
    // Prevent double-click: if already tracking, stop first
    if (trackingActiveRef.current) {
      stopSession();
    }

    // Clear states
    bufferRef.current = [];
    scoreHistoryRef.current = [];
    romHistoryRef.current = [];
    labelHistoryRef.current = [];
    setAngleHistory([]);
    setProbHistory({ "Squat": 0, "Arm Cross": 0, "Body Twist": 0, "Step Jack": 0 });
    setReps(0);
    repsRef.current = 0;
    setAvgScore(0);
    setCurrentScore(0);
    setCurrentLabel("—");
    setBufferFill(0);
    setNotification(null);
    isDemoModeRef.current = false;
    demoTimeRef.current = 0;
    pausedRef.current = false;
    setPaused(false);
    lastRepTimeRef.current = 0;
    setRepCooldown(0);
    repPhaseRef.current = "READY";
    runningPeakRef.current = 0;
    runningValleyRef.current = 180;
    currentLabelRef.current = "\u2014";
    if (cooldownIntervalRef.current) {
      clearInterval(cooldownIntervalRef.current);
      cooldownIntervalRef.current = null;
    }

    trackingActiveRef.current = true;
    setTrackingActive(true);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
      
      // Start tracking loop
      animFrameIdRef.current = requestAnimationFrame(trackingLoop);
    } catch (err) {
      console.warn("Camera init failed, fallback to synthetic demo mode:", err);
      isDemoModeRef.current = true;
      animFrameIdRef.current = requestAnimationFrame(demoLoop);
    }
  };

  const stopSession = () => {
    trackingActiveRef.current = false;
    setTrackingActive(false);
    pausedRef.current = false;
    setPaused(false);
    if (animFrameIdRef.current) {
      cancelAnimationFrame(animFrameIdRef.current);
      animFrameIdRef.current = null;
    }
    if (demoTimeoutRef.current) {
      clearTimeout(demoTimeoutRef.current);
      demoTimeoutRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setBufferFill(0);
    setRepCooldown(0);
    repPhaseRef.current = "READY";
    runningPeakRef.current = 0;
    runningValleyRef.current = 180;
    if (cooldownIntervalRef.current) {
      clearInterval(cooldownIntervalRef.current);
      cooldownIntervalRef.current = null;
    }
  };

  const pauseSession = () => {
    pausedRef.current = true;
    setPaused(true);
  };

  const resumeSession = () => {
    pausedRef.current = false;
    setPaused(false);
  };

  const logSession = async () => {
    if (scoreHistoryRef.current.length === 0) return;
    
    const peakRom = romHistoryRef.current.length > 0 ? Math.max(...romHistoryRef.current) : 0;
    const meanScore = scoreHistoryRef.current.reduce((a, b) => a + b, 0) / scoreHistoryRef.current.length;
    
    // Find most frequent label
    const labelCounts = {};
    let topLabel = "Unknown";
    let maxCount = 0;
    for (const label of labelHistoryRef.current) {
      labelCounts[label] = (labelCounts[label] || 0) + 1;
      if (labelCounts[label] > maxCount) {
        maxCount = labelCounts[label];
        topLabel = label;
      }
    }

    try {
      const res = await fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: selectedPatientId,
          exercise: topLabel,
          peak_rom: parseFloat(peakRom.toFixed(1)),
          mean_score: parseFloat(meanScore.toFixed(1)),
          reps: repsRef.current
        })
      });
      const result = await res.json();
      setNotification(`✅ Session Logged: ${topLabel}, Score: ${meanScore.toFixed(1)}, ROM: ${peakRom.toFixed(1)}°`);
    } catch (err) {
      console.error("Failed to log session:", err);
    }
  };

  // Main Webcam Capture Loop
  const trackingLoop = async (now) => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !trackingActiveRef.current) return;

    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Mirror webcam frame
    ctx.save();
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.restore();

    // Skip processing when paused (keep showing the video feed)
    if (pausedRef.current) {
      animFrameIdRef.current = requestAnimationFrame(trackingLoop);
      return;
    }

    if (landmarkerRef.current && video.readyState >= 2) {
      const result = landmarkerRef.current.detectForVideo(video, now);
      if (result && result.landmarks && result.landmarks.length > 0) {
        const poseLandmarks = result.landmarks[0];
        const worldLandmarks = result.worldLandmarks && result.worldLandmarks.length > 0 
          ? result.worldLandmarks[0] 
          : poseLandmarks;

        // Draw Skeleton overlay on top of frame
        drawSkeleton(ctx, poseLandmarks);

        // Compute 16 joint angles
        const currentAngles = computeAngles(worldLandmarks);
        
        // Left knee angle (triplet index 10: 23-25-27)
        const leftKneeAngle = currentAngles[10];
        setAngleHistory(prev => {
          const next = [...prev, leftKneeAngle];
          if (next.length > 30) next.shift();
          return next;
        });

        // Angle-based rep detection (runs every frame for responsiveness)
        detectRep(currentAngles);

        // Add to sliding window
        bufferRef.current.push(currentAngles);
        if (bufferRef.current.length > 30) {
          bufferRef.current.shift();
        }
        
        setBufferFill(bufferRef.current.length / 30);

        // Strided API scoring to avoid overloading network (every 5 frames)
        if (bufferRef.current.length === 30) {
          apiStrideCounterRef.current++;
          if (apiStrideCounterRef.current >= 5) {
            apiStrideCounterRef.current = 0;
            scoreFrame(bufferRef.current, leftKneeAngle);
          }
        }
      }
    }

    if (trackingActiveRef.current) {
      animFrameIdRef.current = requestAnimationFrame(trackingLoop);
    }
  };

  // Demo synthetic data generator loop (for environments without camera access)
  const demoLoop = () => {
    const canvas = canvasRef.current;
    if (!canvas || !trackingActiveRef.current) return;

    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#000000";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw simple background wireframe text
    ctx.font = "italic 16px Instrument Serif";
    ctx.fillStyle = "rgba(255,255,255,0.4)";
    ctx.textAlign = "center";
    ctx.fillText("\uD83E\uDD16 Demo Mode \u2014 Generating Synthetic Motion data", canvas.width / 2, 35);

    // Skip processing when paused
    if (pausedRef.current) {
      if (trackingActiveRef.current) {
        demoTimeoutRef.current = setTimeout(() => {
          animFrameIdRef.current = requestAnimationFrame(demoLoop);
        }, 40);
      }
      return;
    }

    // Generate sinusoidal knee flexion (0 to 180 deg)
    const t = demoTimeRef.current;
    demoTimeRef.current += 1;

    // Simulate 16 joint angles
    const angles = Array(16).fill(90.0);
    const leftKneeSim = 90.0 + 50.0 * Math.sin(t * 0.15);
    angles[10] = leftKneeSim; // left knee
    angles[11] = leftKneeSim; // right knee
    angles[6] = 80.0 + 30.0 * Math.sin(t * 0.15); // left hip
    angles[7] = 80.0 + 30.0 * Math.sin(t * 0.15); // right hip

    setAngleHistory(prev => {
      const next = [...prev, leftKneeSim];
      if (next.length > 30) next.shift();
      return next;
    });

    // Angle-based rep detection (runs every frame for responsiveness)
    detectRep(angles);

    bufferRef.current.push(angles);
    if (bufferRef.current.length > 30) {
      bufferRef.current.shift();
    }
    setBufferFill(bufferRef.current.length / 30);

    // Draw a synthetic stick figure
    drawSyntheticStickFigure(ctx, t);

    // Strided API scoring
    if (bufferRef.current.length === 30) {
      apiStrideCounterRef.current++;
      if (apiStrideCounterRef.current >= 5) {
        apiStrideCounterRef.current = 0;
        scoreFrame(bufferRef.current, leftKneeSim);
      }
    }

    // Limit frame rate for demo loop
    demoTimeoutRef.current = setTimeout(() => {
      if (trackingActiveRef.current) {
        animFrameIdRef.current = requestAnimationFrame(demoLoop);
      }
    }, 40);
  };

  const drawSyntheticStickFigure = (ctx, t) => {
    const cx = 320;
    const cy = 240;
    const kneeY = cy + 60 + Math.sin(t * 0.15) * 40;
    const joints = {
      head: [cx, cy - 100],
      ls: [cx - 50, cy - 50], rs: [cx + 50, cy - 50],
      lh: [cx - 30, cy + 10], rh: [cx + 30, cy + 10],
      lk: [cx - 30, kneeY], rk: [cx + 30, kneeY],
      la: [cx - 30, kneeY + 50], ra: [cx + 30, kneeY + 50]
    };

    const connections = [
      ["head", "ls"], ["head", "rs"], ["ls", "lh"], ["rs", "rh"],
      ["lh", "rh"], ["lh", "lk"], ["rh", "rk"], ["lk", "la"], ["rk", "ra"]
    ];

    // Draw connections
    ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
    ctx.lineWidth = 4;
    for (const [a, b] of connections) {
      ctx.beginPath();
      ctx.moveTo(joints[a][0], joints[a][1]);
      ctx.lineTo(joints[b][0], joints[b][1]);
      ctx.stroke();
    }

    // Draw joints
    ctx.fillStyle = "#ffffff";
    for (const key in joints) {
      ctx.beginPath();
      ctx.arc(joints[key][0], joints[key][1], 5, 0, 2 * Math.PI);
      ctx.fill();
    }
  };

  const drawSkeleton = (ctx, landmarks) => {
    // Draw mirrored coordinates
    for (const [idxA, idxB] of POSE_CONNECTIONS) {
      const lmA = landmarks[idxA];
      const lmB = landmarks[idxB];
      if (lmA && lmB) {
        // Since frame is mirrored, flip X coordinate for overlay matching
        const xA = (1 - lmA.x) * ctx.canvas.width;
        const yA = lmA.y * ctx.canvas.height;
        const xB = (1 - lmB.x) * ctx.canvas.width;
        const yB = lmB.y * ctx.canvas.height;

        ctx.beginPath();
        ctx.moveTo(xA, yA);
        ctx.lineTo(xB, yB);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.3)";
        ctx.lineWidth = 3;
        ctx.stroke();
      }
    }

    for (const lm of landmarks) {
      if (lm.visibility && lm.visibility < 0.5) continue;
      const x = (1 - lm.x) * ctx.canvas.width;
      const y = lm.y * ctx.canvas.height;

      ctx.beginPath();
      ctx.arc(x, y, 4, 0, 2 * Math.PI);
      ctx.fillStyle = "#ffffff";
      ctx.fill();
      ctx.strokeStyle = "rgba(255,255,255,0.7)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  };

  // ── Angle-based rep detection state machine ──────────────────────────────
  // Detects a full motion cycle: peak → significant descent → significant ascent = 1 rep.
  // Runs every frame for immediate responsiveness.
  const detectRep = (angles) => {
    const label = currentLabelRef.current;
    const angleIdx = EXERCISE_PRIMARY_ANGLE[label];
    if (angleIdx === undefined) return; // no recognised exercise yet

    const angle = angles[angleIdx];
    if (angle === undefined || isNaN(angle)) return;

    // Respect cooldown
    if (Date.now() - lastRepTimeRef.current < REP_COOLDOWN_MS) return;

    const phase = repPhaseRef.current;

    if (phase === "READY") {
      // Track the running peak (highest angle seen)
      if (angle > runningPeakRef.current) runningPeakRef.current = angle;
      // When the angle drops significantly below the peak → entering the rep
      if (runningPeakRef.current - angle > MIN_REP_ANGLE_CHANGE) {
        repPhaseRef.current = "CONTRACTED";
        runningValleyRef.current = angle;
      }
    } else if (phase === "CONTRACTED") {
      // Track the running valley (lowest angle seen)
      if (angle < runningValleyRef.current) runningValleyRef.current = angle;
      // When the angle rises significantly above the valley → rep completed
      if (angle - runningValleyRef.current > MIN_REP_ANGLE_CHANGE) {
        setReps(r => r + 1);
        repsRef.current += 1;
        lastRepTimeRef.current = Date.now();
        repPhaseRef.current = "READY";
        runningPeakRef.current = angle;
        runningValleyRef.current = 180;

        // Start visible countdown timer
        setRepCooldown(4);
        if (cooldownIntervalRef.current) clearInterval(cooldownIntervalRef.current);
        cooldownIntervalRef.current = setInterval(() => {
          setRepCooldown(prev => {
            if (prev <= 1) {
              clearInterval(cooldownIntervalRef.current);
              cooldownIntervalRef.current = null;
              return 0;
            }
            return prev - 1;
          });
        }, 1000);
      }
    }
  };

  const scoreFrame = async (windowBuffer, latestRom) => {
    if (!trackingActiveRef.current) return; // guard against stale async calls
    try {
      const res = await fetch("/api/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ window: [windowBuffer] })
      });
      const data = await res.json();
      if (data.error) return;

      const score = data.score;
      const label = data.label;
      const probs = data.probs;

      // Update metrics
      setCurrentScore(score);
      setCurrentLabel(label);
      setProbHistory(probs);

      scoreHistoryRef.current.push(score);
      romHistoryRef.current.push(latestRom);
      labelHistoryRef.current.push(label);

      // Keep currentLabelRef in sync for the angle-based rep detector
      currentLabelRef.current = label;

      // Session average
      const sum = scoreHistoryRef.current.reduce((a, b) => a + b, 0);
      setAvgScore(sum / scoreHistoryRef.current.length);
    } catch (err) {
      console.error("Inference call failed:", err);
    }
  };

  // Tutorial data matching Python list
  const tutorials = [
    {
      name: "Squat", icon: "🏋️", videoId: "YaXPRqUwItQ",
      tips: [
        "Stand with feet shoulder-width apart, toes slightly out",
        "Hinge at hips first — push them back like sitting into a chair",
        "Keep knees aligned over toes, don't let them cave inward"
      ],
      muscles: ["Quadriceps", "Glutes", "Hamstrings"]
    },
    {
      name: "Arm Cross", icon: "💪", videoId: "-1K0m5ywRcY",
      tips: [
        "Stand tall, extend arms to sides at shoulder height (T position)",
        "Sweep arms forward across your body, crossing one over the other",
        "Keep shoulders down — avoid shrugging toward ears"
      ],
      muscles: ["Shoulders", "Chest", "Upper Back"]
    },
    {
      name: "Body Twist", icon: "🔄", videoId: "f4Qah0bQTIo",
      tips: [
        "Stand with feet shoulder-width apart, knees slightly bent",
        "Raise arms to chest height with elbows bent at 90 degrees",
        "Initiate the twist from your core, not your arms"
      ],
      muscles: ["Obliques", "Core", "Lower Back"]
    },
    {
      name: "Step Jack", icon: "⭐", videoId: "JHdVMkRBuRA",
      tips: [
        "Stand tall with feet together and arms at your sides",
        "Step right foot out while raising arms overhead",
        "Low-impact alternative to jumping jacks — gentle on joints"
      ],
      muscles: ["Full Body", "Shoulders", "Cardio"]
    }
  ];

  return (
    <div className="relative min-h-screen pt-28 pb-12 px-6 md:px-12 lg:px-16 z-10 w-full flex flex-col justify-start">
      {/* Background video (120% scale, same as landing page) */}
      <FadingVideo
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260418_080021_d598092b-c4c2-4e53-8e46-94cf9064cd50.mp4"
        className="absolute left-1/2 top-0 -translate-x-1/2 object-cover object-top z-0"
        style={{ width: "120%", height: "120%" }}
      />
      <div className="absolute inset-0 bg-black/70 z-0" />

      {/* Main Grid */}
      <div className="relative z-10 w-full max-w-7xl mx-auto flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Side: Setup & Video (Span 7) */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          
          {/* Patient Selector / Profile Header */}
          <div className="liquid-glass rounded-[1.25rem] p-6 flex flex-wrap gap-6 items-center justify-between">
            <div className="flex-1 min-w-[200px]">
              <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-2 font-medium">
                Patient Profile
              </label>
              {user ? (
                <div className="font-heading italic text-3xl text-white mt-1 pl-1">
                  {patient ? patient.name : user.name}
                </div>
              ) : (
                <select
                  value={selectedPatientId}
                  onChange={e => setSelectedPatientId(Number(e.target.value))}
                  className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white select-none focus:outline-none focus:border-white/20"
                >
                  {patients.map(p => (
                    <option key={p.id} value={p.id} className="bg-black text-white">{p.name}</option>
                  ))}
                </select>
              )}
            </div>
            
            {patient && (
              <div className="flex flex-col text-right">
                <span className="text-[10px] uppercase tracking-widest text-white/40 font-medium">Diagnosis</span>
                <span className="font-heading italic text-2xl text-white mt-1">{patient.condition}</span>
              </div>
            )}
          </div>

          {/* Video Feed card */}
          <div className="liquid-glass rounded-[1.5rem] p-4 flex flex-col relative overflow-hidden">
            <div className="flex justify-between items-center mb-3 px-2">
              <h2 className="font-heading italic text-2xl text-white">📹 Live Session Feed</h2>
              {trackingActive && (
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-white animate-pulse" style={{ boxShadow: "0 0 8px #fff" }} />
                  <span className="text-xs text-white/80 font-body">Tracking Active</span>
                </div>
              )}
            </div>

            {/* Video container */}
            <div className="relative aspect-video w-full rounded-[1rem] overflow-hidden bg-black/40 border border-white/5 flex items-center justify-center">
              {/* Invisible HTML5 video */}
              <video
                ref={videoRef}
                className="hidden"
                width="640"
                height="480"
                playsInline
                muted
              />
              {/* Visible overlay canvas */}
              <canvas
                ref={canvasRef}
                className="w-full h-full object-cover"
                width="640"
                height="480"
              />
              
              {!trackingActive && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 text-center p-4">
                  <span className="text-4xl mb-4 select-none">📷</span>
                  <h3 className="font-heading italic text-3xl text-white mb-2">Ready to Start</h3>
                  <p className="text-sm text-white/60 font-body max-w-[28ch] leading-relaxed mb-6">
                    Connect your webcam, stand in full view of the camera, and start tracking to analyze your range of motion.
                  </p>
                  <button
                    onClick={startSession}
                    className="liquid-glass-strong rounded-full px-8 py-2.5 text-sm font-semibold text-white tracking-wide hover:bg-white/5"
                  >
                    Start Session
                  </button>
                </div>
              )}
            </div>

            {/* Controls */}
            {trackingActive && (
              <div className="grid grid-cols-3 gap-4 mt-4">
                <button
                  onClick={stopSession}
                  className="liquid-glass rounded-full py-2.5 text-sm font-medium text-white/90 hover:bg-white/5 hover:text-white border border-white/10"
                >
                  Stop Session
                </button>
                <button
                  onClick={paused ? resumeSession : pauseSession}
                  className={`liquid-glass rounded-full py-2.5 text-sm font-medium hover:bg-white/5 border border-white/10 ${
                    paused ? "text-green-400 hover:text-green-300" : "text-amber-400 hover:text-amber-300"
                  }`}
                >
                  {paused ? "▶ Resume" : "⏸ Pause"}
                </button>
                <button
                  onClick={logSession}
                  className="liquid-glass-strong rounded-full py-2.5 text-sm font-medium text-white hover:opacity-95"
                >
                  Log Session
                </button>
              </div>
            )}

            {/* Buffer progress bar */}
            {trackingActive && bufferFill < 1 && (
              <div className="mt-4 px-2">
                <div className="flex justify-between text-[10px] text-white/50 uppercase tracking-widest mb-1.5 font-medium">
                  <span>Building temporal window...</span>
                  <span>{Math.round(bufferFill * 100)}%</span>
                </div>
                <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-white rounded-full transition-all duration-300"
                    style={{ width: `${bufferFill * 100}%` }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Active Prescription Card */}
          {selectedPresc && (
            <div className="liquid-glass rounded-[1.25rem] p-6 flex flex-col md:flex-row gap-6 md:items-center justify-between">
              <div className="flex-1">
                <span className="text-[10px] uppercase tracking-widest text-white/40 block mb-1">Prescribed Exercise</span>
                <span className="font-heading italic text-3xl text-white">{selectedPresc.exercise}</span>
                {selectedPresc.notes && (
                  <p className="text-xs text-white/60 font-body mt-2 leading-relaxed">
                    Notes: {selectedPresc.notes}
                  </p>
                )}
              </div>
              <div className="flex gap-4">
                <div className="liquid-glass p-3 px-4 rounded-[0.75rem] text-center min-w-[90px]">
                  <div className="text-[9px] uppercase tracking-wider text-white/50 mb-0.5">Target Reps</div>
                  <div className="font-heading italic text-2xl text-white leading-none">{selectedPresc.target_reps}</div>
                </div>
                <div className="liquid-glass p-3 px-4 rounded-[0.75rem] text-center min-w-[90px]">
                  <div className="text-[9px] uppercase tracking-wider text-white/50 mb-0.5">Target ROM</div>
                  <div className="font-heading italic text-2xl text-white leading-none">{selectedPresc.target_rom}°</div>
                </div>
              </div>
            </div>
          )}

          {notification && (
            <div className="liquid-glass rounded-full px-6 py-3 text-sm text-white/95 font-body flex items-center justify-between relative overflow-hidden border border-white/10" style={{ textShadow: "0 0 8px rgba(255,255,255,0.2)" }}>
              <span>{notification}</span>
              <button onClick={() => setNotification(null)} className="text-white/40 hover:text-white text-xs ml-4">Dismiss</button>
            </div>
          )}
        </div>

        {/* Right Side: Metrics (Span 5) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          
          {/* Live Score Ring Card */}
          <div className="liquid-glass rounded-[1.5rem] p-6 flex flex-col items-center">
            <h3 className="text-xs uppercase tracking-widest text-white/50 font-medium mb-6 font-body">Accuracy Score</h3>
            
            <div className="w-[150px] h-[150px] rounded-full liquid-glass-strong flex flex-col items-center justify-center relative select-none">
              <span className="font-heading italic text-6xl text-white leading-none" style={{ textShadow: "0 0 15px rgba(255,255,255,0.3)" }}>
                {Math.round(currentScore)}
              </span>
              <span className="text-[10px] text-white/50 uppercase tracking-wider font-body font-light mt-1">/ 100</span>
            </div>

            <div className="text-center mt-6">
              <span className="text-[10px] uppercase tracking-widest text-white/40 font-medium block">Classified Action</span>
              <span className="font-heading italic text-3xl text-white mt-1 block">{currentLabel}</span>
            </div>
          </div>

          {/* Session Quick Metrics */}
          <div className="grid grid-cols-2 gap-4">
            <div className="liquid-glass p-5 rounded-[1.25rem] text-center flex flex-col justify-center">
              <span className="text-[10px] uppercase tracking-widest text-white/50 mb-1">Reps Counted</span>
              <span className="font-heading italic text-4xl text-white leading-none">{reps}</span>
              {repCooldown > 0 && (
                <span className="text-[10px] uppercase tracking-widest text-amber-400/80 mt-2 font-medium animate-pulse">
                  Cooldown {repCooldown}s
                </span>
              )}
            </div>
            <div className="liquid-glass p-5 rounded-[1.25rem] text-center flex flex-col justify-center">
              <span className="text-[10px] uppercase tracking-widest text-white/50 mb-1">Session Avg</span>
              <span className="font-heading italic text-4xl text-white leading-none">{Math.round(avgScore)}</span>
            </div>
          </div>

          {/* Live Bar Chart */}
          <div className="liquid-glass rounded-[1.25rem] p-6">
            <h3 className="text-xs uppercase tracking-widest text-white/50 font-medium mb-4">Class Probabilities</h3>
            <BarChart data={probHistory} color="#ffffff" />
          </div>

          {/* Live Line Waveform */}
          <div className="liquid-glass rounded-[1.25rem] p-6">
            <h3 className="text-xs uppercase tracking-widest text-white/50 font-medium mb-2">Live Waveform (Left Knee)</h3>
            <LineChart data={angleHistory} color="#ffffff" />
          </div>
        </div>

      </div>

      {/* Tutorial Section (Span Full) */}
      <div className="relative z-10 w-full max-w-7xl mx-auto mt-16 pt-8 border-t border-white/5">
        <h2 className="font-heading italic text-4xl text-white mb-1">📖 Clinical Tutorials</h2>
        <p className="text-sm text-white/60 font-body mb-8">Review form guidelines and target groups before initiating exercise sets.</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {tutorials.map(tut => (
            <div key={tut.name} className="liquid-glass rounded-[1.5rem] p-6 flex flex-col md:flex-row gap-6 hover:bg-white/[0.02] transition-all duration-300">
              
              {/* Embedded video player */}
              <div className="w-full md:w-[220px] aspect-video rounded-[0.75rem] overflow-hidden bg-black border border-white/5 shrink-0">
                <iframe
                  className="w-full h-full"
                  src={`https://www.youtube.com/embed/${tut.videoId}?autoplay=0&mute=1`}
                  title={`${tut.name} Tutorial`}
                  frameBorder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>

              {/* Text content */}
              <div className="flex-1 flex flex-col justify-between">
                <div>
                  <h3 className="font-heading italic text-2xl text-white mb-3">
                    {tut.icon} {tut.name}
                  </h3>
                  <div className="flex flex-col gap-1.5">
                    {tut.tips.map((tip, idx) => (
                      <div key={idx} className="text-xs text-white/70 leading-relaxed flex items-start gap-1.5">
                        <span className="text-white/40">•</span>
                        <span>{tip}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-4">
                  <span className="text-[9px] uppercase tracking-widest text-white/40 block mb-1">Target Muscles</span>
                  <div className="flex flex-wrap gap-1.5">
                    {tut.muscles.map(m => (
                      <span key={m} className="bg-white/5 text-[10px] text-white/80 px-2.5 py-0.5 rounded-full border border-white/5">
                        {m}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

window.PatientDashboard = PatientDashboard;
