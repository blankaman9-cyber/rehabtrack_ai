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
  return (
    <div className="relative bg-black w-full min-h-screen selection:bg-white selection:text-black">
      {/* Section 1: Hero */}
      <Hero />

      {/* Section 2: Capabilities */}
      <Capabilities />
    </div>
  );
};

// Render React App
const container = document.getElementById("root");
const root = ReactDOM.createRoot(container);
root.render(<App />);
