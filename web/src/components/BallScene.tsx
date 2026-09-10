"use client";

/**
 * Real-ball hero scene (FLOW-true): the user's Blender football
 * (dirty_football, LOD1 + 1K diffuse, cool-graded via lighting),
 * served as a 430KB .glb. Slow idle spin, clamped mouse parallax,
 * gentle float. Reduced motion / WebGL failure -> oracle SVG poster.
 */
import { Component, Suspense, useEffect, useRef, useState, type ReactNode } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import { useReducedMotion } from "motion/react";
import * as THREE from "three";
import { Mascot } from "./Mascot";
import { Tooltip } from "./Tooltip";

const BALL_URL = "/models/ball.glb";

function Ball() {
  const ref = useRef<THREE.Group>(null);
  const { pointer } = useThree();
  const gltf = useGLTF(BALL_URL);

  useFrame((state, delta) => {
    const g = ref.current;
    if (!g) return;
    const t = Math.min(delta, 0.05);
    g.rotation.y += t * 0.35;
    // Clamped mouse parallax tilt (±8deg eased toward pointer).
    const tx = THREE.MathUtils.clamp(pointer.y * 0.14, -0.14, 0.14);
    const ty = THREE.MathUtils.clamp(pointer.x * 0.14, -0.14, 0.14);
    g.rotation.x += (tx - g.rotation.x) * Math.min(1, t * 3);
    g.rotation.z += (ty - g.rotation.z) * Math.min(1, t * 3);
    // Gentle float matching the old CSS rhythm (~4s cycle).
    g.position.y = Math.sin(state.clock.elapsedTime * (Math.PI / 2)) * 0.08;
  });

  return (
    <group ref={ref} scale={1.6}>
      <primitive object={gltf.scene.clone()} />
    </group>
  );
}

function StaticBall() {
  const gltf = useGLTF(BALL_URL);
  return (
    <group scale={1.6} rotation={[0.3, 0.8, 0]}>
      <primitive object={gltf.scene.clone()} />
    </group>
  );
}

function Scene() {
  const reduced = useReducedMotion();
  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: [0, 0, 5], fov: 40 }}
      gl={{ antialias: true, alpha: true }}
      style={{ background: "transparent" }}
    >
      {/* Cool key + warm rim: grades the dirty textures toward the palette. */}
      <ambientLight intensity={0.55} />
      <directionalLight position={[4, 5, 6]} intensity={1.6} color="#dfe9ff" />
      <directionalLight position={[-5, -2, -4]} intensity={0.5} color="#ffd9c2" />
      <Suspense fallback={null}>{reduced ? <StaticBall /> : <Ball />}</Suspense>
    </Canvas>
  );
}

class ErrorFallback extends Component<
  { className?: string; children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <div className={`flex items-center justify-center ${this.props.className ?? ""}`}>
          <Mascot mood="oracle" size={132} />
        </div>
      );
    }
    return this.props.children;
  }
}

/** Hero ball with tooltip CTA (mirrors the old HeroMascot contract). */
export function HeroBall({ className = "" }: { className?: string }) {
  return (
    <div className="mascot-float">
      <Tooltip tip="Ask me anything — I read 23 pre-match signals. No odds, no tips.">
        <a href="/predict" aria-label="Ask the oracle to predict a match">
          <BallSceneSafe className={className} />
        </a>
      </Tooltip>
    </div>
  );
}
/** Mount-gated (never SSR'd) + error boundary with SVG poster fallback. */
export function BallSceneSafe({ className = "" }: { className?: string }) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
    useGLTF.preload(BALL_URL);
  }, []);
  if (!mounted) {
    return (
      <div className={`flex items-center justify-center ${className}`}>
        <Mascot mood="oracle" size={132} />
      </div>
    );
  }
  return (
    <ErrorFallback className={className}>
      <Scene />
    </ErrorFallback>
  );
}
