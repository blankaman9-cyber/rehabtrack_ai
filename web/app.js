// Suppress benign Framer Motion dev warnings about list keys
const originalError = console.error;
console.error = (...args) => {
  if (
    /Framer Motion/i.test(args[0]) ||
    /React does not recognize/i.test(args[0]) ||
    /Warning: Each child in a list should have a unique/i.test(args[0])
  ) {
    return;
  }
  originalError.apply(console, args);
};

const App = () => {
  const [role, setRole] = React.useState(null);
  const [user, setUser] = React.useState(null);

  const handleLoginSuccess = (authenticatedUser) => {
    setUser(authenticatedUser);
  };

  const handleSignOut = () => {
    setRole(null);
    setUser(null);
  };

  const isAuthenticated = !!user;

  return (
    <div className="relative bg-black w-full min-h-screen text-white selection:bg-white selection:text-black font-body">
      {/* Top Navbar */}
      <Navbar role={role} user={user} onSwitchRole={handleSignOut} />

      {/* Main Page Rendering */}
      {!role && <RoleSelection onSelectRole={setRole} />}
      
      {role && !isAuthenticated && (
        <Login
          role={role}
          onLoginSuccess={handleLoginSuccess}
          onBack={() => setRole(null)}
        />
      )}
      
      {role === "patient" && isAuthenticated && <PatientDashboard user={user} />}
      {role === "doctor" && isAuthenticated && <DoctorDashboard user={user} />}
    </div>
  );
};

// Render React App
const container = document.getElementById("root");
const root = ReactDOM.createRoot(container);
root.render(<App />);
