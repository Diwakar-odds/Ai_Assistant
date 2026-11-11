import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import type { OrbState } from '../../contexts/DashboardContext';

export interface ArcReactorRingsProps {
  /** Mood state: 'focused' | 'calm' | 'happy' | 'stressed' | 'neutral' */
  mood?: string;
  /** Project completion 0-100 */
  projectProgress?: number;
  /** Project name */
  projectName?: string;
  /** System health 0-100 */
  systemHealth?: number;
  /** When true, switches orb into alert/error mode */
  dangerMode?: boolean;
  /** Live 5-state 4D orb mode */
  orbState?: OrbState;
  /** Live voice amplitude (0-100) driving outer surface particle vibration */
  audioLevel?: number;
}

interface StateVisualConfig {
  primary: THREE.Color;
  secondary: THREE.Color;
  accent: THREE.Color;
  speed: number;
  noiseFreq: number;
  displacement: number;
  particleVibration: number;
  jaggedness: number;
  swirl: number;
  alphaBoost: number;
}

const STATE_PALETTES: Record<OrbState, StateVisualConfig> = {
  idle: {
    primary: new THREE.Color('#2563eb'),   // Deep Cobalt Blue
    secondary: new THREE.Color('#7c3aed'), // Indigo Violet
    accent: new THREE.Color('#c026d3'),    // Soft Magenta Aura
    speed: 0.55,
    noiseFreq: 1.55,
    displacement: 0.085,
    particleVibration: 0.035,
    jaggedness: 0.0,
    swirl: 0.12,
    alphaBoost: 0.88,
  },
  listening: {
    primary: new THREE.Color('#00f3ff'),   // Electric Cyan
    secondary: new THREE.Color('#3b82f6'), // Vivid Azure
    accent: new THREE.Color('#a855f7'),    // Violet Highlight
    speed: 1.25,
    noiseFreq: 2.05,
    displacement: 0.14,
    particleVibration: 0.12,
    jaggedness: 0.0,
    swirl: 0.28,
    alphaBoost: 1.05,
  },
  speaking: {
    primary: new THREE.Color('#00d4ff'),   // Cyan Crest
    secondary: new THREE.Color('#8b5cf6'), // Electric Purple
    accent: new THREE.Color('#ec4899'),    // Neon Pink-Magenta
    speed: 1.55,
    noiseFreq: 2.25,
    displacement: 0.18,
    particleVibration: 0.14,
    jaggedness: 0.0,
    swirl: 0.32,
    alphaBoost: 1.12,
  },
  processing: {
    primary: new THREE.Color('#f59e0b'),   // Amber Gold
    secondary: new THREE.Color('#f97316'), // Warm Orange
    accent: new THREE.Color('#8b5cf6'),    // Cosmic Violet
    speed: 2.15,
    noiseFreq: 2.55,
    displacement: 0.15,
    particleVibration: 0.10,
    jaggedness: 0.12,
    swirl: 1.25,
    alphaBoost: 1.08,
  },
  error: {
    primary: new THREE.Color('#ef4444'),   // Crimson Red
    secondary: new THREE.Color('#f97316'), // Ember Orange
    accent: new THREE.Color('#fb7185'),    // Strobe Rose
    speed: 2.9,
    noiseFreq: 3.15,
    displacement: 0.21,
    particleVibration: 0.19,
    jaggedness: 1.0,
    swirl: 0.55,
    alphaBoost: 1.18,
  },
};

// Ashima Arts 4D Simplex Noise (WebGL1 & WebGL2 compatible GLSL)
const SIMPLEX_4D_GLSL = `
vec4 mod289(vec4 x) {
  return x - floor(x * (1.0 / 289.0)) * 289.0;
}
float mod289(float x) {
  return x - floor(x * (1.0 / 289.0)) * 289.0;
}
vec4 permute(vec4 x) {
  return mod289(((x * 34.0) + 1.0) * x);
}
float permute(float x) {
  return mod289(((x * 34.0) + 1.0) * x);
}
vec4 taylorInvSqrt(vec4 r) {
  return 1.79284291400159 - 0.85373472095314 * r;
}
float taylorInvSqrt(float r) {
  return 1.79284291400159 - 0.85373472095314 * r;
}
vec4 grad4(float j, vec4 ip) {
  const vec4 ones = vec4(1.0, 1.0, 1.0, -1.0);
  vec4 p, s;
  p.xyz = floor(fract(vec3(j) * ip.xyz) * 7.0) * ip.z - 1.0;
  p.w = 1.5 - dot(abs(p.xyz), ones.xyz);
  s = vec4(lessThan(p, vec4(0.0)));
  p.xyz = p.xyz + (s.xyz * 2.0 - 1.0) * s.www;
  return p;
}
float snoise4D(vec4 v) {
  const vec4 C = vec4(
    0.138196601125011,
    0.276393202250021,
    0.414589803375032,
    -0.447213595499958
  );
  vec4 i = floor(v + dot(v, vec4(0.309016994374947451)));
  vec4 x0 = v - i + dot(i, C.xxxx);
  vec4 i0;
  vec3 isX = step(x0.yzw, x0.xxx);
  vec3 isYZ = step(x0.zww, x0.yyz);
  i0.x = isX.x + isX.y + isX.z;
  i0.yzw = 1.0 - isX;
  i0.y += isYZ.x + isYZ.y;
  i0.zw += 1.0 - isYZ.xy;
  i0.z += isYZ.z;
  i0.w += 1.0 - isYZ.z;
  vec4 i3 = clamp(i0, 0.0, 1.0);
  vec4 i2 = clamp(i0 - 1.0, 0.0, 1.0);
  vec4 i1 = clamp(i0 - 2.0, 0.0, 1.0);
  vec4 x1 = x0 - i1 + C.xxxx;
  vec4 x2 = x0 - i2 + C.yyyy;
  vec4 x3 = x0 - i3 + C.zzzz;
  vec4 x4 = x0 + C.wwww;
  i = mod289(i);
  float j0 = permute(permute(permute(permute(i.w) + i.z) + i.y) + i.x);
  vec4 j1 = permute(permute(permute(permute(
    i.w + vec4(i1.w, i2.w, i3.w, 1.0))
    + i.z + vec4(i1.z, i2.z, i3.z, 1.0))
    + i.y + vec4(i1.y, i2.y, i3.y, 1.0))
    + i.x + vec4(i1.x, i2.x, i3.x, 1.0));
  vec4 ip = vec4(1.0 / 294.0, 1.0 / 49.0, 1.0 / 7.0, 0.0);
  vec4 p0 = grad4(j0, ip);
  vec4 p1 = grad4(j1.x, ip);
  vec4 p2 = grad4(j1.y, ip);
  vec4 p3 = grad4(j1.z, ip);
  vec4 p4 = grad4(j1.w, ip);
  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;
  p4 *= taylorInvSqrt(dot(p4, p4));
  vec3 m0 = max(0.6 - vec3(dot(x0, x0), dot(x1, x1), dot(x2, x2)), 0.0);
  vec2 m1 = max(0.6 - vec2(dot(x3, x3), dot(x4, x4)), 0.0);
  m0 = m0 * m0;
  m1 = m1 * m1;
  return 49.0 * (
    dot(m0 * m0, vec3(dot(p0, x0), dot(p1, x1), dot(p2, x2))) +
    dot(m1 * m1, vec2(dot(p3, x3), dot(p4, x4)))
  );
}

float orbField(vec3 dir, float wTime, float freq, float audioLvl, float jagged) {
  float n1 = snoise4D(vec4(dir * freq, wTime * 0.42));
  float n2 = 0.45 * snoise4D(vec4(dir * (freq * 2.1) + vec3(3.1, -1.7, 2.4), wTime * 0.85));
  float wave = n1 + n2;
  float harmonic = sin(dir.y * 7.0 + wTime * 3.4) * cos(dir.x * 6.0 - wTime * 2.7) * audioLvl * 0.55;
  float spikes = abs(snoise4D(vec4(dir * (freq * 3.4), wTime * 1.9))) * jagged * 0.85;
  return wave + harmonic + spikes;
}
`;

function createQuadLatticeGeometry(latSteps = 44, lonSteps = 60, radius = 0.92): THREE.BufferGeometry {
  const vertices: number[] = [];
  const pointOnSphere = (latIdx: number, lonIdx: number): [number, number, number] => {
    const phi = (latIdx / latSteps) * Math.PI;
    const theta = (lonIdx / lonSteps) * Math.PI * 2;
    const sinPhi = Math.sin(phi);
    return [
      radius * sinPhi * Math.cos(theta),
      radius * Math.cos(phi),
      radius * sinPhi * Math.sin(theta),
    ];
  };

  for (let i = 0; i < latSteps; i++) {
    for (let j = 0; j < lonSteps; j++) {
      const p0 = pointOnSphere(i, j);
      const pDown = pointOnSphere(i + 1, j);
      vertices.push(p0[0], p0[1], p0[2], pDown[0], pDown[1], pDown[2]);

      if (i > 0) {
        const pNextLon = pointOnSphere(i, (j + 1) % lonSteps);
        vertices.push(p0[0], p0[1], p0[2], pNextLon[0], pNextLon[1], pNextLon[2]);
      }
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
  return geometry;
}

function createParticleHaloGeometry(count = 2200, baseRadius = 0.96): THREE.BufferGeometry {
  const positions = new Float32Array(count * 3);
  const phases = new Float32Array(count);
  const shells = new Float32Array(count);
  const sizes = new Float32Array(count);
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));

  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2;
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = goldenAngle * i + (Math.sin(i * 12.9898) * 0.25);

    const nx = Math.cos(theta) * r;
    const ny = y;
    const nz = Math.sin(theta) * r;

    // Outer halo concentrates near the undulating surface with delicate outer dust
    const isOuterHalo = i % 3 === 0;
    const shellOffset = isOuterHalo ? (0.04 + ((i * 73) % 100) / 420) : (((i * 37) % 100) / 1400);
    const radius = baseRadius + shellOffset;

    positions[i * 3] = nx * radius;
    positions[i * 3 + 1] = ny * radius;
    positions[i * 3 + 2] = nz * radius;

    phases[i] = (i * 0.61803398875) * Math.PI * 2;
    shells[i] = isOuterHalo ? 1.0 : 0.42;
    sizes[i] = isOuterHalo ? (1.9 + ((i * 19) % 10) * 0.28) : (1.25 + ((i * 11) % 10) * 0.18);
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('aPhase', new THREE.BufferAttribute(phases, 1));
  geometry.setAttribute('aShell', new THREE.BufferAttribute(shells, 1));
  geometry.setAttribute('aSize', new THREE.BufferAttribute(sizes, 1));
  return geometry;
}

const ArcReactorRings = ({
  mood = 'neutral',
  projectProgress = 0,
  projectName = '',
  systemHealth = 100,
  dangerMode = false,
  orbState = 'idle',
  audioLevel = 0,
}: ArcReactorRingsProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [hovered, setHovered] = useState(false);

  const resolvedState: OrbState = dangerMode ? 'error' : orbState;
  const targetRef = useRef<{ state: OrbState; audioLevel: number }>({
    state: resolvedState,
    audioLevel: Math.max(0, Math.min(100, audioLevel)),
  });

  useEffect(() => {
    targetRef.current.state = resolvedState;
    targetRef.current.audioLevel = Math.max(0, Math.min(100, audioLevel));
  }, [resolvedState, audioLevel]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let rafId = 0;
    let renderer: THREE.WebGLRenderer | null = null;
    let fallbackCanvas: HTMLCanvasElement | null = null;
    let resizeObserver: ResizeObserver | null = null;

    const width = Math.max(180, container.clientWidth || 280);
    const height = Math.max(180, container.clientHeight || 280);

    try {
      renderer = new THREE.WebGLRenderer({
        alpha: true,
        antialias: true,
        powerPreference: 'high-performance',
      });
      renderer.setClearColor(0x000000, 0);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(width, height);
      renderer.domElement.style.width = '100%';
      renderer.domElement.style.height = '100%';
      renderer.domElement.style.display = 'block';
      renderer.domElement.style.pointerEvents = 'none';
      container.appendChild(renderer.domElement);

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 20);
      camera.position.z = 3.55;

      const orbGroup = new THREE.Group();
      scene.add(orbGroup);

      const initialCfg = STATE_PALETTES[targetRef.current.state] || STATE_PALETTES.idle;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);

      const sharedUniforms = {
        uTime: { value: 0 },
        uAudioLevel: { value: 0 },
        uDisplacement: { value: initialCfg.displacement },
        uParticleVibration: { value: initialCfg.particleVibration },
        uNoiseFreq: { value: initialCfg.noiseFreq },
        uJaggedness: { value: initialCfg.jaggedness },
        uAlphaBoost: { value: initialCfg.alphaBoost },
        uColorPrimary: { value: initialCfg.primary.clone() },
        uColorSecondary: { value: initialCfg.secondary.clone() },
        uColorAccent: { value: initialCfg.accent.clone() },
        uPixelRatio: { value: dpr },
      };

      // 0. Dark cosmic translucent backing sphere so 4D mesh contrasts crisply on light or dark UIs
      const darkCoreGeometry = new THREE.SphereGeometry(0.875, 48, 48);
      const darkCoreMaterial = new THREE.ShaderMaterial({
        uniforms: sharedUniforms,
        transparent: true,
        depthWrite: false,
        blending: THREE.NormalBlending,
        side: THREE.FrontSide,
        vertexShader: `
          uniform float uTime;
          uniform float uAudioLevel;
          uniform float uDisplacement;
          uniform float uNoiseFreq;
          uniform float uJaggedness;
          varying vec3 vNormalDir;
          varying vec3 vPos;
          varying float vField;
          ${SIMPLEX_4D_GLSL}
          void main() {
            vec3 dir = normalize(position);
            float f = orbField(dir, uTime, uNoiseFreq, uAudioLevel, uJaggedness);
            float amp = uDisplacement * (0.72 + uAudioLevel * 0.8);
            vec3 displaced = position + dir * (f * amp * 0.82);
            vPos = displaced;
            vField = f;
            vNormalDir = normalize(normalMatrix * normal);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 uColorPrimary;
          uniform vec3 uColorSecondary;
          uniform vec3 uColorAccent;
          uniform float uAudioLevel;
          varying vec3 vNormalDir;
          varying vec3 vPos;
          varying float vField;
          void main() {
            float facing = abs(dot(normalize(vNormalDir), vec3(0.0, 0.0, 1.0)));
            float fresnel = pow(1.0 - facing, 2.0);
            float sweep = smoothstep(-0.75, 0.75, vPos.x * 0.72 - vPos.y * 0.35 + vPos.z * 0.35);
            vec3 stateCol = mix(uColorPrimary, uColorAccent, sweep);
            vec3 cosmic = mix(vec3(0.025, 0.04, 0.10), stateCol, 0.24 + fresnel * 0.34 + uAudioLevel * 0.14);
            float alpha = clamp(0.46 + facing * 0.26 + max(0.0, vField) * 0.08, 0.0, 0.74);
            gl_FragColor = vec4(cosmic, alpha);
          }
        `,
      });
      const darkCoreMesh = new THREE.Mesh(darkCoreGeometry, darkCoreMaterial);
      orbGroup.add(darkCoreMesh);

      // 1. Volumetric translucent inner aura sphere (subtle magenta-indigo depth)
      const coreGeometry = new THREE.SphereGeometry(0.86, 48, 48);
      const coreMaterial = new THREE.ShaderMaterial({
        uniforms: sharedUniforms,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        side: THREE.FrontSide,
        vertexShader: `
          uniform float uTime;
          uniform float uAudioLevel;
          uniform float uDisplacement;
          uniform float uNoiseFreq;
          uniform float uJaggedness;
          varying vec3 vNormalDir;
          varying vec3 vPos;
          varying float vField;
          ${SIMPLEX_4D_GLSL}
          void main() {
            vec3 dir = normalize(position);
            float f = orbField(dir, uTime, uNoiseFreq, uAudioLevel, uJaggedness);
            float amp = uDisplacement * (0.7 + uAudioLevel * 0.8);
            vec3 displaced = position + dir * (f * amp * 0.85);
            vPos = displaced;
            vField = f;
            vNormalDir = normalize(normalMatrix * normal);
            gl_Position = projectionMatrix * modelViewMatrix * vec4(displaced, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 uColorPrimary;
          uniform vec3 uColorSecondary;
          uniform vec3 uColorAccent;
          uniform float uAudioLevel;
          uniform float uAlphaBoost;
          varying vec3 vNormalDir;
          varying vec3 vPos;
          varying float vField;
          void main() {
            float fresnel = pow(1.0 - abs(dot(normalize(vNormalDir), vec3(0.0, 0.0, 1.0))), 2.2);
            float sweep = smoothstep(-0.75, 0.75, vPos.x * 0.72 - vPos.y * 0.35 + vPos.z * 0.35);
            vec3 baseCol = mix(uColorPrimary, uColorSecondary, sweep);
            vec3 finalCol = mix(baseCol, uColorAccent, smoothstep(0.15, 0.95, fresnel + vField * 0.35));
            float alpha = (0.08 + fresnel * 0.34 + max(0.0, vField) * 0.10 + uAudioLevel * 0.14) * uAlphaBoost;
            gl_FragColor = vec4(finalCol, clamp(alpha, 0.0, 0.55));
          }
        `,
      });
      const coreMesh = new THREE.Mesh(coreGeometry, coreMaterial);
      orbGroup.add(coreMesh);

      // 2. Smooth 4D curvilinear quad lattice wireframe
      const latticeGeometry = createQuadLatticeGeometry(44, 60, 0.92);
      const latticeMaterial = new THREE.ShaderMaterial({
        uniforms: sharedUniforms,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        vertexShader: `
          uniform float uTime;
          uniform float uAudioLevel;
          uniform float uDisplacement;
          uniform float uNoiseFreq;
          uniform float uJaggedness;
          varying vec3 vDir;
          varying float vField;
          varying float vViewFacing;
          ${SIMPLEX_4D_GLSL}
          void main() {
            vec3 dir = normalize(position);
            float f = orbField(dir, uTime, uNoiseFreq, uAudioLevel, uJaggedness);
            float amp = uDisplacement + uAudioLevel * 0.14;
            vec3 displaced = position + dir * (f * amp);
            vec4 mvPos = modelViewMatrix * vec4(displaced, 1.0);
            vec3 mvNorm = normalize(normalMatrix * dir);
            vDir = dir;
            vField = f;
            vViewFacing = abs(mvNorm.z);
            gl_Position = projectionMatrix * mvPos;
          }
        `,
        fragmentShader: `
          uniform vec3 uColorPrimary;
          uniform vec3 uColorSecondary;
          uniform vec3 uColorAccent;
          uniform float uAudioLevel;
          uniform float uAlphaBoost;
          varying vec3 vDir;
          varying float vField;
          varying float vViewFacing;
          void main() {
            float sweep = smoothstep(-0.8, 0.85, vDir.x * 0.78 - vDir.y * 0.25 + vField * 0.25);
            vec3 grad = mix(uColorPrimary, uColorSecondary, smoothstep(0.0, 0.55, sweep));
            grad = mix(grad, uColorAccent, smoothstep(0.42, 1.0, sweep));
            float ridge = smoothstep(-0.1, 0.85, vField);
            float rimBoost = pow(1.0 - vViewFacing, 1.35);
            vec3 col = mix(grad, vec3(1.0), ridge * 0.26 + uAudioLevel * 0.18);
            float alpha = (0.30 + ridge * 0.36 + rimBoost * 0.32 + uAudioLevel * 0.20) * uAlphaBoost;
            gl_FragColor = vec4(col, clamp(alpha, 0.12, 0.92));
          }
        `,
      });
      const latticeLines = new THREE.LineSegments(latticeGeometry, latticeMaterial);
      orbGroup.add(latticeLines);

      // 3. Outer vibrating surface particle halo (reacts directly to voice intensity)
      const particleGeometry = createParticleHaloGeometry(2200, 0.95);
      const particleMaterial = new THREE.ShaderMaterial({
        uniforms: sharedUniforms,
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        vertexShader: `
          attribute float aPhase;
          attribute float aShell;
          attribute float aSize;
          uniform float uTime;
          uniform float uAudioLevel;
          uniform float uDisplacement;
          uniform float uParticleVibration;
          uniform float uNoiseFreq;
          uniform float uJaggedness;
          uniform float uPixelRatio;
          varying vec3 vDir;
          varying float vField;
          varying float vSpark;
          ${SIMPLEX_4D_GLSL}
          void main() {
            vec3 dir = normalize(position);
            float f = orbField(dir, uTime, uNoiseFreq, uAudioLevel, uJaggedness);
            float surfaceDisp = f * (uDisplacement + uAudioLevel * 0.12);

            // Real-time radial acoustic vibration synced to speaking loudness
            float acousticOsc = sin(uTime * 22.0 + aPhase * 3.0) * 0.55 + cos(uTime * 13.0 - aPhase * 2.0) * 0.45;
            float vibrationAmp = uParticleVibration + uAudioLevel * (0.28 + 0.24 * aShell);
            float radialBurst = acousticOsc * vibrationAmp + (uAudioLevel * 0.16 * aShell);

            // High-frequency jagged tremble in error state
            float errorShake = sin(uTime * 38.0 + aPhase * 5.0) * uJaggedness * 0.045;

            vec3 tangent = normalize(cross(dir, abs(dir.y) < 0.9 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0)));
            vec3 displaced = position + dir * (surfaceDisp + radialBurst + errorShake)
              + tangent * (sin(uTime * 7.5 + aPhase) * (0.015 + uAudioLevel * 0.06));

            vec4 mvPosition = modelViewMatrix * vec4(displaced, 1.0);
            float voiceSizeBoost = 1.0 + uAudioLevel * (0.85 + 0.65 * aShell);
            gl_PointSize = clamp(aSize * voiceSizeBoost * uPixelRatio * (3.1 / max(0.8, -mvPosition.z)), 1.5, 18.0);
            vDir = dir;
            vField = f;
            vSpark = 0.55 + 0.45 * sin(uTime * 4.5 + aPhase);
            gl_Position = projectionMatrix * mvPosition;
          }
        `,
        fragmentShader: `
          uniform vec3 uColorPrimary;
          uniform vec3 uColorSecondary;
          uniform vec3 uColorAccent;
          uniform float uAudioLevel;
          uniform float uAlphaBoost;
          varying vec3 vDir;
          varying float vField;
          varying float vSpark;
          void main() {
            vec2 centered = gl_PointCoord - vec2(0.5);
            float distSq = dot(centered, centered);
            if (distSq > 0.25) discard;
            float softGlow = exp(-distSq * 16.0);

            float sweep = smoothstep(-0.85, 0.85, vDir.x * 0.78 - vDir.y * 0.3 + vField * 0.25);
            vec3 col = mix(uColorPrimary, uColorSecondary, smoothstep(0.0, 0.55, sweep));
            col = mix(col, uColorAccent, smoothstep(0.45, 1.0, sweep));
            col = mix(col, vec3(1.0), softGlow * (0.35 + uAudioLevel * 0.35));

            float alpha = softGlow * (0.42 + vSpark * 0.38 + uAudioLevel * 0.35) * uAlphaBoost;
            gl_FragColor = vec4(col, clamp(alpha, 0.0, 1.0));
          }
        `,
      });
      const particlePoints = new THREE.Points(particleGeometry, particleMaterial);
      orbGroup.add(particlePoints);

      const handleResize = () => {
        if (!container || !renderer) return;
        const w = Math.max(120, container.clientWidth);
        const h = Math.max(120, container.clientHeight);
        const curDpr = Math.min(window.devicePixelRatio || 1, 2);
        renderer.setPixelRatio(curDpr);
        renderer.setSize(w, h);
        sharedUniforms.uPixelRatio.value = curDpr;
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
      };

      if (typeof ResizeObserver !== 'undefined') {
        resizeObserver = new ResizeObserver(handleResize);
        resizeObserver.observe(container);
      }

      let lastTime = performance.now();
      let currentSpeed = initialCfg.speed;
      let currentSwirl = initialCfg.swirl;
      let smoothedAudio = 0;

      const animate = (now: number) => {
        rafId = requestAnimationFrame(animate);
        const dt = Math.min(0.05, Math.max(0.001, (now - lastTime) * 0.001));
        lastTime = now;

        const targetState = targetRef.current.state;
        const palette = STATE_PALETTES[targetState] || STATE_PALETTES.idle;
        const targetAudio = targetRef.current.audioLevel / 100;

        // Smooth audio & palette interpolation
        const audioLerp = targetAudio > smoothedAudio ? 0.34 : 0.16;
        smoothedAudio += (targetAudio - smoothedAudio) * audioLerp;
        sharedUniforms.uAudioLevel.value = smoothedAudio;

        const lerpRate = Math.min(1, dt * 6.5);
        sharedUniforms.uColorPrimary.value.lerp(palette.primary, lerpRate);
        sharedUniforms.uColorSecondary.value.lerp(palette.secondary, lerpRate);
        sharedUniforms.uColorAccent.value.lerp(palette.accent, lerpRate);

        sharedUniforms.uDisplacement.value += (palette.displacement - sharedUniforms.uDisplacement.value) * lerpRate;
        sharedUniforms.uParticleVibration.value += (palette.particleVibration - sharedUniforms.uParticleVibration.value) * lerpRate;
        sharedUniforms.uNoiseFreq.value += (palette.noiseFreq - sharedUniforms.uNoiseFreq.value) * lerpRate;
        sharedUniforms.uJaggedness.value += (palette.jaggedness - sharedUniforms.uJaggedness.value) * lerpRate;
        sharedUniforms.uAlphaBoost.value += (palette.alphaBoost - sharedUniforms.uAlphaBoost.value) * lerpRate;

        currentSpeed += (palette.speed - currentSpeed) * lerpRate;
        currentSwirl += (palette.swirl - currentSwirl) * lerpRate;

        sharedUniforms.uTime.value += dt * (currentSpeed + smoothedAudio * 1.15);

        orbGroup.rotation.y += dt * (0.18 + currentSwirl * 0.45 + smoothedAudio * 0.25);
        orbGroup.rotation.x = Math.sin(sharedUniforms.uTime.value * 0.35) * 0.14;
        orbGroup.rotation.z = Math.cos(sharedUniforms.uTime.value * 0.28) * 0.08;

        const breathScale = targetState === 'error'
          ? 1.0 + Math.sin(now * 0.018) * 0.035 + smoothedAudio * 0.06
          : 1.0 + Math.sin(sharedUniforms.uTime.value * 1.1) * 0.018 + smoothedAudio * 0.075;
        orbGroup.scale.setScalar(breathScale);

        renderer?.render(scene, camera);
      };

      rafId = requestAnimationFrame(animate);

      return () => {
        cancelAnimationFrame(rafId);
        resizeObserver?.disconnect();
        darkCoreGeometry.dispose();
        darkCoreMaterial.dispose();
        coreGeometry.dispose();
        coreMaterial.dispose();
        latticeGeometry.dispose();
        latticeMaterial.dispose();
        particleGeometry.dispose();
        particleMaterial.dispose();
        if (renderer) {
          renderer.dispose();
          renderer.domElement.remove();
        }
      };
    } catch {
      // Lightweight Canvas 2D fallback when WebGL is unavailable (e.g., jsdom / software test env)
      fallbackCanvas = document.createElement('canvas');
      fallbackCanvas.width = width;
      fallbackCanvas.height = height;
      fallbackCanvas.style.width = '100%';
      fallbackCanvas.style.height = '100%';
      fallbackCanvas.style.display = 'block';
      fallbackCanvas.style.pointerEvents = 'none';
      container.appendChild(fallbackCanvas);

      const ctx = fallbackCanvas.getContext('2d');
      let t = 0;

      const drawFallback = () => {
        rafId = requestAnimationFrame(drawFallback);
        if (!ctx || !fallbackCanvas) return;
        const w = fallbackCanvas.width;
        const h = fallbackCanvas.height;
        const cx = w / 2;
        const cy = h / 2;
        const cfg = STATE_PALETTES[targetRef.current.state] || STATE_PALETTES.idle;
        const amp = targetRef.current.audioLevel / 100;
        t += 0.035 * cfg.speed;

        ctx.clearRect(0, 0, w, h);
        const baseR = Math.min(w, h) * 0.34;
        const count = 90;

        for (let i = 0; i < count; i++) {
          const angle = (i / count) * Math.PI * 2 + t * 0.35;
          const wave = Math.sin(angle * 4 + t * 2) * (6 + amp * 18);
          const r = baseR + wave;
          const px = cx + Math.cos(angle) * r;
          const py = cy + Math.sin(angle) * r;
          ctx.beginPath();
          ctx.arc(px, py, 1.8 + amp * 2.2, 0, Math.PI * 2);
          ctx.fillStyle = i % 2 === 0 ? `#${cfg.primary.getHexString()}` : `#${cfg.accent.getHexString()}`;
          ctx.fill();
        }
      };

      if (ctx) {
        rafId = requestAnimationFrame(drawFallback);
      }

      return () => {
        cancelAnimationFrame(rafId);
        fallbackCanvas?.remove();
      };
    }
  }, []);

  const stateColorHex = `#${(STATE_PALETTES[resolvedState] || STATE_PALETTES.idle).primary.getHexString()}`;

  return (
    <div
      ref={containerRef}
      data-orb-state={resolvedState}
      data-audio-level={Math.round(audioLevel)}
      className="absolute inset-0 overflow-visible"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {hovered && (projectName || systemHealth !== undefined) && (
        <div
          className="pointer-events-none absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md px-2.5 py-1 text-[10px] font-mono backdrop-blur-md border z-20"
          style={{
            backgroundColor: 'rgba(10, 14, 24, 0.78)',
            borderColor: `${stateColorHex}55`,
            color: stateColorHex,
          }}
        >
          {resolvedState.toUpperCase()} • {mood} • Health {systemHealth}%
          {projectName ? ` • ${projectName.slice(0, 12)} ${Math.round(projectProgress)}%` : ''}
        </div>
      )}
    </div>
  );
};

export default ArcReactorRings;
