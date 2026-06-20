// Trends line chart mapping values onto a time series grid
const TrendsLineChart = ({ dates, values, label, color = "#ffffff", height = 200 }) => {
  if (!values || values.length === 0) {
    return (
      <div className="flex items-center justify-center text-white/40 text-xs italic bg-white/[0.01] rounded-[0.75rem]" style={{ height }}>
        No historical session data.
      </div>
    );
  }

  const minVal = Math.min(...values, 0);
  const maxVal = Math.max(...values, 100);
  const range = maxVal - minVal || 1;

  const points = values.map((val, i) => {
    const x = (i / (values.length - 1 || 1)) * 100;
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
      <div className="absolute top-0 left-0 text-[9px] text-white/30">{Math.round(maxVal)}{label}</div>
      <div className="absolute bottom-0 left-0 text-[9px] text-white/30">{Math.round(minVal)}{label}</div>
      <div className="absolute bottom-0 right-0 text-[9px] text-white/50">Points: {values.length}</div>
    </div>
  );
};

const DoctorDashboard = () => {
  const [patients, setPatients] = React.useState([]);
  const [selectedPatient, setSelectedPatient] = React.useState(null);
  const [sessions, setSessions] = React.useState([]);
  const [prescriptions, setPrescriptions] = React.useState([]);
  const [trends, setTrends] = React.useState({ rom: { dates: [], values: [] }, score: { dates: [], values: [] } });

  // Form states
  const [prescExercise, setPrescExercise] = React.useState("Squat");
  const [prescReps, setPrescReps] = React.useState(10);
  const [prescRom, setPrescRom] = React.useState(90.0);
  const [prescNotes, setPrescNotes] = React.useState("");

  const [newPatientName, setNewPatientName] = React.useState("");
  const [newPatientAge, setNewPatientAge] = React.useState(30);
  const [newPatientCondition, setNewPatientCondition] = React.useState("");
  const [newPatientPassword, setNewPatientPassword] = React.useState("password");

  const [showAddPresc, setShowAddPresc] = React.useState(false);
  const [showAddPatient, setShowAddPatient] = React.useState(false);

  const [notification, setNotification] = React.useState(null);

  // Fetch directory list
  const loadPatients = () => {
    fetch("/api/patients")
      .then(res => res.json())
      .then(data => {
        setPatients(data);
        if (data.length > 0 && !selectedPatient) {
          setSelectedPatient(data[0]);
        } else if (selectedPatient) {
          // Keep current patient detail updated
          const updated = data.find(p => p.id === selectedPatient.id);
          if (updated) setSelectedPatient(updated);
        }
      })
      .catch(err => console.error("Error loading patients:", err));
  };

  React.useEffect(() => {
    loadPatients();
  }, []);

  // Fetch stats & trends for selected patient
  React.useEffect(() => {
    if (!selectedPatient) return;
    const pid = selectedPatient.id;

    // Load sessions list
    fetch(`/api/sessions/${pid}`)
      .then(res => res.json())
      .then(data => setSessions(data))
      .catch(err => console.error(err));

    // Load active prescriptions
    fetch(`/api/prescriptions/${pid}`)
      .then(res => res.json())
      .then(data => setPrescriptions(data))
      .catch(err => console.error(err));

    // Load trends
    fetch(`/api/trends/${pid}`)
      .then(res => res.json())
      .then(data => setTrends(data))
      .catch(err => console.error(err));
  }, [selectedPatient]);

  const handleAddPrescription = async (e) => {
    e.preventDefault();
    if (!selectedPatient) return;

    try {
      const res = await fetch("/api/prescriptions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          patient_id: selectedPatient.id,
          exercise: prescExercise,
          target_reps: prescReps,
          target_rom: prescRom,
          notes: prescNotes
        })
      });
      const data = await res.json();
      if (!res.ok) {
        setNotification(`❌ Error: ${data.error || 'Failed to add prescription'}`);
        return;
      }
      setNotification(`✅ Prescription assigned: ${prescExercise}`);
      
      // Reload prescriptions
      const pRes = await fetch(`/api/prescriptions/${selectedPatient.id}`);
      const pData = await pRes.json();
      setPrescriptions(pData);

      // Reset form
      setPrescNotes("");
      setShowAddPresc(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRegisterPatient = async (e) => {
    e.preventDefault();
    if (!newPatientName) return;

    try {
      const res = await fetch("/api/patients", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newPatientName,
          age: newPatientAge,
          condition: newPatientCondition,
          password: newPatientPassword
        })
      });
      const data = await res.json();
      if (!res.ok) {
        setNotification(`❌ Error: ${data.error || 'Failed to register patient'}`);
        return;
      }
      setNotification(`✅ Patient registered: ${newPatientName}`);

      // Reload list
      loadPatients();

      // Reset form
      setNewPatientName("");
      setNewPatientAge(30);
      setNewPatientCondition("");
      setNewPatientPassword("password");
      setShowAddPatient(false);
    } catch (err) {
      console.error(err);
    }
  };

  const handleRemovePatient = async () => {
    if (!selectedPatient) return;
    if (!window.confirm(`Are you sure you want to permanently delete patient ${selectedPatient.name} and all of their prescription and session records?`)) {
      return;
    }

    try {
      const pid = selectedPatient.id;
      const name = selectedPatient.name;
      const res = await fetch(`/api/patients/${pid}`, {
        method: "DELETE"
      });
      const data = await res.json();
      
      if (res.ok) {
        setNotification(`✅ Patient removed: ${name}`);
        // Reload list and handle selection
        fetch("/api/patients")
          .then(r => r.json())
          .then(data => {
            setPatients(data);
            if (data.length > 0) {
              setSelectedPatient(data[0]);
            } else {
              setSelectedPatient(null);
            }
          });
      } else {
        setNotification(`❌ Error: ${data.error || "Could not remove patient"}`);
      }
    } catch (err) {
      console.error(err);
      setNotification("❌ Network error while removing patient.");
    }
  };

  // KPI aggregates
  const totalSessions = sessions.length;
  const avgAccuracy = trends.score.values.length > 0 
    ? trends.score.values.reduce((a, b) => a + b, 0) / trends.score.values.length 
    : 0;
  const peakROM = trends.rom.values.length > 0 
    ? Math.max(...trends.rom.values) 
    : 0;
  const lastSessionDate = sessions.length > 0 
    ? sessions[0].session_date.substring(0, 10) 
    : "—";

  return (
    <div className="relative min-h-screen pt-28 pb-12 z-10 w-full flex flex-col justify-start">
      {/* Background Video */}
      <FadingVideo
        src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260418_094631_d30ab262-45ee-4b7d-99f3-5d5848c8ef13.mp4"
        className="absolute inset-0 w-full h-full object-cover z-0"
      />
      <div className="absolute inset-0 bg-black/80 z-0" />

      <div className="relative z-10 w-full max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Side: Directory Sidebar (Span 3) */}
        <div className="lg:col-span-3 flex flex-col gap-6">
          <div className="liquid-glass rounded-[1.5rem] p-6 flex flex-col min-h-[400px]">
            <h3 className="font-heading italic text-2xl text-white mb-4">🏥 Directory</h3>
            
            <div className="flex flex-col gap-2 overflow-y-auto max-h-[300px] pr-2">
              {patients.map(p => (
                <div
                  key={p.id}
                  onClick={() => setSelectedPatient(p)}
                  className={`p-3.5 rounded-[0.75rem] cursor-pointer transition-all duration-200 ${
                    selectedPatient?.id === p.id
                      ? "bg-white/10 border-l-2 border-white"
                      : "bg-white/[0.01] hover:bg-white/5"
                  }`}
                >
                  <div className="text-sm font-semibold text-white">{p.name}</div>
                  <div className="text-[10px] text-white/50 mt-1 uppercase tracking-wider">{p.condition}</div>
                </div>
              ))}
            </div>

            <button
              onClick={() => setShowAddPatient(true)}
              className="liquid-glass border border-white/10 rounded-full py-2 text-xs font-semibold uppercase tracking-wider mt-auto text-white hover:bg-white/5"
            >
              + Register Patient
            </button>
          </div>
        </div>

        {/* Right Side: Dashboard Details (Span 9) */}
        <div className="lg:col-span-9 flex flex-col gap-6">
          {selectedPatient && (
            <>
              {/* Patient Header Details */}
              <div className="liquid-glass rounded-[1.25rem] p-6 flex flex-wrap justify-between items-center gap-4">
                <div>
                  <span className="text-[10px] uppercase tracking-widest text-white/40 block mb-1">Active Patient</span>
                  <h2 className="font-heading italic text-4xl text-white leading-tight">{selectedPatient.name}</h2>
                  <p className="text-xs text-white/60 font-body font-light mt-1">
                    Age {selectedPatient.age} · {selectedPatient.condition}
                  </p>
                </div>
                
                <div className="flex items-center gap-4 flex-wrap">
                  {notification && (
                    <div className="liquid-glass rounded-full px-5 py-2 text-xs text-white flex items-center gap-4 border border-white/10">
                      <span>{notification}</span>
                      <button onClick={() => setNotification(null)} className="text-white/40 hover:text-white">✕</button>
                    </div>
                  )}
                  
                  <button
                    onClick={handleRemovePatient}
                    className="liquid-glass border border-red-500/20 text-red-400 hover:bg-red-500/10 rounded-full px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wider transition-all duration-200"
                  >
                    🗑️ Remove Patient
                  </button>
                </div>
              </div>

              {/* KPI Cards Row */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="liquid-glass p-4 rounded-[1rem] text-center">
                  <div className="text-[10px] uppercase tracking-widest text-white/50 mb-1">Total Sessions</div>
                  <div className="font-heading italic text-3xl text-white mt-1">{totalSessions}</div>
                </div>
                <div className="liquid-glass p-4 rounded-[1rem] text-center">
                  <div className="text-[10px] uppercase tracking-widest text-white/50 mb-1">Avg Accuracy</div>
                  <div className="font-heading italic text-3xl text-white mt-1">{avgAccuracy.toFixed(1)}%</div>
                </div>
                <div className="liquid-glass p-4 rounded-[1rem] text-center">
                  <div className="text-[10px] uppercase tracking-widest text-white/50 mb-1">Peak ROM</div>
                  <div className="font-heading italic text-3xl text-white mt-1">{peakROM.toFixed(1)}°</div>
                </div>
                <div className="liquid-glass p-4 rounded-[1rem] text-center">
                  <div className="text-[10px] uppercase tracking-widest text-white/50 mb-1">Last Session</div>
                  <div className="font-heading italic text-2xl text-white mt-1.5">{lastSessionDate}</div>
                </div>
              </div>

              {/* Trend Graphs Section */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="liquid-glass rounded-[1.25rem] p-6">
                  <h3 className="text-xs uppercase tracking-widest text-white/50 font-medium mb-4">📐 ROM Trend Over Time</h3>
                  <TrendsLineChart dates={trends.rom.dates} values={trends.rom.values} label="°" color="#ffffff" />
                </div>
                <div className="liquid-glass rounded-[1.25rem] p-6">
                  <h3 className="text-xs uppercase tracking-widest text-white/50 font-medium mb-4">🎯 Accuracy Progress</h3>
                  <TrendsLineChart dates={trends.score.dates} values={trends.score.values} label="%" color="#b0b0b0" />
                </div>
              </div>

              {/* Sessions Table */}
              <div className="liquid-glass rounded-[1.5rem] p-6">
                <h3 className="font-heading italic text-2xl text-white mb-4">📋 Session History Log</h3>
                
                {sessions.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-white/5 text-[10px] uppercase tracking-widest text-white/45">
                          <th className="py-3 px-4 font-semibold">Date</th>
                          <th className="py-3 px-4 font-semibold">Exercise</th>
                          <th className="py-3 px-4 font-semibold text-right">Reps</th>
                          <th className="py-3 px-4 font-semibold text-right">Peak ROM</th>
                          <th className="py-3 px-4 font-semibold text-right">Avg Score</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.02]">
                        {sessions.map(s => (
                          <tr key={s.id} className="text-xs font-body hover:bg-white/[0.01] transition-colors">
                            <td className="py-3 px-4 text-white/80">{s.session_date ? s.session_date.substring(0, 16) : '—'}</td>
                            <td className="py-3 px-4 text-white font-medium">{s.exercise}</td>
                            <td className="py-3 px-4 text-right text-white/90">{s.reps}</td>
                            <td className="py-3 px-4 text-right text-white/90">{s.peak_rom != null ? s.peak_rom.toFixed(1) : '—'}°</td>
                            <td className="py-3 px-4 text-right text-white/95 font-semibold">{s.mean_score != null ? s.mean_score.toFixed(1) : '—'}/100</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-white/40 italic py-4">No exercise sets logged for this patient yet.</p>
                )}
              </div>

              {/* Prescription Management Card */}
              <div className="liquid-glass rounded-[1.5rem] p-6 flex flex-col">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="font-heading italic text-2xl text-white">📋 Prescription Protocols</h3>
                  <button
                    onClick={() => setShowAddPresc(true)}
                    className="liquid-glass border border-white/10 rounded-full px-4 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-white hover:bg-white/5"
                  >
                    + Assign Protocol
                  </button>
                </div>

                {prescriptions.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-white/5 text-[10px] uppercase tracking-widest text-white/45">
                          <th className="py-3 px-4 font-semibold">Assigned</th>
                          <th className="py-3 px-4 font-semibold">Exercise</th>
                          <th className="py-3 px-4 font-semibold text-right">Target Reps</th>
                          <th className="py-3 px-4 font-semibold text-right">Target ROM</th>
                          <th className="py-3 px-4 font-semibold">Notes</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.02]">
                        {prescriptions.map(p => (
                          <tr key={p.id} className="text-xs font-body hover:bg-white/[0.01] transition-colors">
                            <td className="py-3 px-4 text-white/60">{p.assigned_at.substring(0, 10)}</td>
                            <td className="py-3 px-4 text-white font-medium">{p.exercise}</td>
                            <td className="py-3 px-4 text-right text-white/90">{p.target_reps}</td>
                            <td className="py-3 px-4 text-right text-white/90">{p.target_rom}°</td>
                            <td className="py-3 px-4 text-white/70 max-w-[200px] truncate" title={p.notes}>{p.notes || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-white/40 italic py-4">No active prescriptions defined.</p>
                )}
              </div>
            </>
          )}
        </div>

      </div>

      {/* MODALS */}
      {/* 1. Assign Prescription Protocol Modal */}
      {showAddPresc && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="liquid-glass rounded-[1.5rem] p-8 max-w-md w-full border border-white/10 shadow-2xl relative">
            <h3 className="font-heading italic text-3xl text-white mb-6">📝 Assign Protocol</h3>
            
            <form onSubmit={handleAddPrescription} className="flex flex-col gap-5">
              <div>
                <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-1">Select Exercise</label>
                <select
                  value={prescExercise}
                  onChange={e => setPrescExercise(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white select-none focus:outline-none"
                >
                  <option value="Squat" className="bg-black">Squat</option>
                  <option value="Arm Cross" className="bg-black">Arm Cross</option>
                  <option value="Body Twist" className="bg-black">Body Twist</option>
                  <option value="Step Jack" className="bg-black">Step Jack</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-1">Target Reps</label>
                  <input
                    type="number"
                    value={prescReps}
                    onChange={e => setPrescReps(Number(e.target.value))}
                    min="1" max="100"
                    className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-1">Target ROM (°)</label>
                  <input
                    type="number"
                    value={prescRom}
                    onChange={e => setPrescRom(parseFloat(e.target.value))}
                    min="10" max="180"
                    className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-1">Clinical Notes</label>
                <input
                  type="text"
                  placeholder="e.g. Keep spine neutral, 3 sets"
                  value={prescNotes}
                  onChange={e => setPrescNotes(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white focus:outline-none"
                />
              </div>

              <div className="flex gap-4 mt-4">
                <button
                  type="button"
                  onClick={() => setShowAddPresc(false)}
                  className="flex-1 liquid-glass border border-white/10 rounded-full py-2.5 text-sm font-semibold text-white/80 hover:bg-white/5"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 liquid-glass-strong rounded-full py-2.5 text-sm font-semibold text-white hover:opacity-95"
                >
                  Assign
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 2. Register Patient Modal */}
      {showAddPatient && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="liquid-glass rounded-[1.5rem] p-8 max-w-md w-full border border-white/10 shadow-2xl relative">
            <h3 className="font-heading italic text-3xl text-white mb-6">➕ Register Patient</h3>
            
            <form onSubmit={handleRegisterPatient} className="flex flex-col gap-5">
              <div>
                <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-1">Patient Full Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Arjun Sharma"
                  value={newPatientName}
                  onChange={e => setNewPatientName(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-1">Age</label>
                <input
                  type="number"
                  required
                  value={newPatientAge}
                  onChange={e => setNewPatientAge(Number(e.target.value))}
                  min="5" max="110"
                  className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-1">Condition / Diagnosis</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Post-ACL reconstruction"
                  value={newPatientCondition}
                  onChange={e => setNewPatientCondition(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-widest text-white/50 block mb-1">Password</label>
                <input
                  type="password"
                  required
                  placeholder="Set patient password"
                  value={newPatientPassword}
                  onChange={e => setNewPatientPassword(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2 text-sm text-white focus:outline-none"
                />
              </div>

              <div className="flex gap-4 mt-4">
                <button
                  type="button"
                  onClick={() => setShowAddPatient(false)}
                  className="flex-1 liquid-glass border border-white/10 rounded-full py-2.5 text-sm font-semibold text-white/80 hover:bg-white/5"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 liquid-glass-strong rounded-full py-2.5 text-sm font-semibold text-white hover:opacity-95"
                >
                  Register
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

window.DoctorDashboard = DoctorDashboard;
