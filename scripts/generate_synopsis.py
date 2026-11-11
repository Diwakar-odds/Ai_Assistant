"""
PULSAR Major Project Synopsis Generator - Advanced Hybrid Cloud-Edge Architecture
Compliant with AKTU / KIT Guidelines:
- Number of Pages: 10–15 pages (Target: Exactly 14 Pages)
- Paper Size: A4 (210mm x 297mm)
- Font: Times New Roman
- Font Size: 12 pt for body text, 14 pt for headings
- Line Spacing: 1.15
- Text Alignment: Justified
- Group Leader: Diwakar Chaurasia (23016501000073)
- Members:
  1. Raghav Bajpai (230165010000119)
  2. Ghanshyam Jha (23016501000076)
  3. Abhishek Sharma (23016501000010)
"""

import os
import subprocess
import re

OUTPUT_DIR = r"d:\Projects\Ai_Assistant\docs"
HTML_PATH = os.path.join(OUTPUT_DIR, "PULSAR_Major_Project_Synopsis.html")
PDF_PATH = os.path.join(OUTPUT_DIR, "PULSAR_Major_Project_Synopsis.pdf")
MD_PATH = os.path.join(OUTPUT_DIR, "PULSAR_Major_Project_Synopsis.md")
DESKTOP_PDF_PATH = r"C:\Users\bdiwa\Desktop\PULSAR_Major_Project_Synopsis.pdf"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def build_html():
    css = """
    @page {
      size: A4 portrait;
      margin: 0;
    }
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      padding: 0;
      background: #eef2f5;
      font-family: 'Times New Roman', Times, serif;
      color: #111111;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
    @media screen {
      .page {
        margin: 25px auto;
        box-shadow: 0 5px 20px rgba(0,0,0,0.18);
      }
    }
    .page {
      width: 210mm;
      height: 297mm;
      max-height: 297mm;
      padding: 13.5mm 17.5mm;
      position: relative;
      background: #ffffff;
      page-break-after: always;
      break-after: page;
      overflow: hidden;
    }
    .page-border {
      position: absolute;
      top: 8.5mm;
      left: 10.5mm;
      right: 10.5mm;
      bottom: 8.5mm;
      border: 1.5px solid #111111;
      pointer-events: none;
    }
    .page-footer {
      position: absolute;
      bottom: 10.5mm;
      left: 0;
      right: 0;
      text-align: center;
      font-size: 11pt;
      font-family: 'Times New Roman', Times, serif;
    }
    h1.sec-title {
      font-size: 14pt;
      font-weight: bold;
      text-align: center;
      margin-top: 0;
      margin-bottom: 6pt;
      text-transform: uppercase;
      letter-spacing: 0.3px;
      line-height: 1.15;
    }
    h2.sub-title {
      font-size: 13pt;
      font-weight: bold;
      margin-top: 5pt;
      margin-bottom: 2pt;
      line-height: 1.15;
    }
    p {
      font-size: 12pt;
      line-height: 1.15;
      margin: 3pt 0;
      text-align: justify;
    }
    ul {
      margin: 2.5pt 0;
      padding-left: 17pt;
    }
    li {
      font-size: 12pt;
      line-height: 1.15;
      margin-bottom: 2pt;
      text-align: justify;
    }
    ol {
      margin: 2.5pt 0;
      padding-left: 17pt;
    }
    ol li {
      font-size: 12pt;
      line-height: 1.15;
      margin-bottom: 2pt;
      text-align: justify;
    }
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      margin: 4pt 0;
      font-size: 10pt;
    }
    table.data-table th, table.data-table td {
      border: 1px solid #222222;
      padding: 3pt 4.5pt;
      vertical-align: top;
      line-height: 1.15;
    }
    table.data-table th {
      font-weight: bold;
      background-color: #f7f7f7;
    }
    .fig-box {
      text-align: center;
      margin: 3.5pt 0;
    }
    .fig-cap {
      font-size: 10pt;
      font-weight: bold;
      text-align: center;
      margin-top: 3pt;
      margin-bottom: 2pt;
      line-height: 1.15;
    }
    """

    pages = []

    # =========================================================================
    # PAGE 1: TITLE PAGE
    # =========================================================================
    p1 = """
    <div class="page" id="page-1">
      <div class="page-border"></div>
      <div style="text-align: center; padding-top: 10mm;">
        <div style="font-size: 26pt; font-weight: bold; letter-spacing: 2px; margin-bottom: 8pt;">“PULSAR”</div>
        <div style="font-size: 13pt; font-weight: bold; line-height: 1.3; max-width: 165mm; margin: 0 auto 16pt auto;">
          An Autonomous Hybrid Cloud-Edge Agentic AI Platform with Multimodal Vision, Spatial Gesture Interaction, and Native Windows Automation
        </div>
        
        <div style="font-size: 13pt; font-weight: bold; letter-spacing: 0.5px; margin-bottom: 4pt;">SYNOPSIS OF MAJOR PROJECT</div>
        <div style="font-size: 11pt; margin-bottom: 2pt;">of</div>
        <div style="font-size: 12.5pt; font-weight: bold; margin-bottom: 2pt;">Bachelor of Technology</div>
        <div style="font-size: 11pt; margin-bottom: 2pt;">in</div>
        <div style="font-size: 12.5pt; font-weight: bold; margin-bottom: 6pt;">Computer Science & Engineering</div>
        <div style="font-size: 11pt; margin-bottom: 8pt;">By</div>

        <table style="width: 98%; margin: 0 auto 18pt auto; border-collapse: collapse; font-size: 10.5pt;">
          <thead>
            <tr style="background: #fafafa;">
              <th style="border: 1px solid #222; padding: 4.5pt 6pt; font-weight: bold; width: 8%;">S.No.</th>
              <th style="border: 1px solid #222; padding: 4.5pt 8pt; font-weight: bold; width: 38%;">Student Name</th>
              <th style="border: 1px solid #222; padding: 4.5pt 8pt; font-weight: bold; width: 26%;">Roll Number</th>
              <th style="border: 1px solid #222; padding: 4.5pt 8pt; font-weight: bold; width: 28%;">Branch & Section</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="border: 1px solid #222; padding: 4.5pt 6pt; text-align: center;">1</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: left; font-weight: bold;">Diwakar Chaurasia (Leader)</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: center;">23016501000073</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: center;">CSE</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 4.5pt 6pt; text-align: center;">2</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: left;">Raghav Bajpai</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: center;">230165010000119</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: center;">CSE</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 4.5pt 6pt; text-align: center;">3</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: left;">Ghanshyam Jha</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: center;">23016501000076</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: center;">CSE</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 4.5pt 6pt; text-align: center;">4</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: left;">Abhishek Sharma</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: center;">23016501000010</td>
              <td style="border: 1px solid #222; padding: 4.5pt 8pt; text-align: center;">CSE</td>
            </tr>
          </tbody>
        </table>

        <!-- KIT Logo / Emblem -->
        <div style="margin: 0 auto 10pt auto; width: 140px; text-align: center;">
          <svg width="125" height="38" viewBox="0 0 200 65" xmlns="http://www.w3.org/2000/svg">
            <path d="M15 45 L35 15 L55 45 L42 45 L35 32 L28 45 Z" fill="#999999" opacity="0.6"/>
            <path d="M30 48 L48 20 L66 48 L54 48 L48 37 L42 48 Z" fill="#1b499c" opacity="0.4"/>
            <text x="75" y="48" font-family="'Arial Black', Arial, sans-serif" font-size="44" font-weight="900" fill="#143975" letter-spacing="1">KIT</text>
            <circle cx="152" cy="18" r="6" fill="#44aa44"/>
            <path d="M152 10 L152 26 M144 18 L160 18 M146 12 L158 24 M146 24 L158 12" stroke="#ffffff" stroke-width="2"/>
            <text x="144" y="30" font-family="Arial, sans-serif" font-size="9" font-weight="bold" fill="#555555">Estd. 2004</text>
          </svg>
        </div>

        <div style="font-size: 12.5pt; font-weight: bold; margin-bottom: 3pt;">Kanpur Institute of Technology, Kanpur</div>
        <div style="font-size: 11pt; font-weight: bold; margin-bottom: 4pt;">Dr. A.P.J. Abdul Kalam Technical University, Lucknow</div>
        <div style="font-size: 10.5pt; font-weight: bold;">Academic Session: 2026–27</div>
      </div>
      <div class="page-footer">Page 1</div>
    </div>
    """
    pages.append(p1)

    # =========================================================================
    # PAGE 2: DECLARATION
    # =========================================================================
    p2 = """
    <div class="page" id="page-2">
      <div class="page-border"></div>
      <div style="padding-top: 10mm;">
        <h1 class="sec-title" style="margin-bottom: 14pt;">DECLARATION</h1>
        
        <p style="margin-bottom: 16pt;">
          We hereby declare that this submission is our own work and that, to the best of our knowledge and 
          belief, it contains no material previously published or written by another person nor material which to 
          a substantial extent has been accepted for the award of any other degree or diploma by the university 
          or other institute of higher learning, except where due acknowledgement has been made in the text.
        </p>

        <div style="margin-bottom: 16pt; font-size: 11pt; line-height: 1.35;">
          <div style="font-weight: bold; margin-bottom: 6pt;">Student Signatures:</div>
          
          <table style="width: 100%; border-collapse: collapse; font-size: 10.5pt;">
            <tr>
              <td style="width: 50%; padding: 6pt 4pt; vertical-align: top; border: none;">
                <div>Signature: __________________________</div>
                <div><strong>Diwakar Chaurasia (Leader)</strong></div>
                <div>Roll No: 23016501000073</div>
              </td>
              <td style="width: 50%; padding: 6pt 4pt; vertical-align: top; border: none;">
                <div>Signature: __________________________</div>
                <div><strong>Raghav Bajpai</strong></div>
                <div>Roll No: 230165010000119</div>
              </td>
            </tr>
            <tr>
              <td style="width: 50%; padding: 8pt 4pt; vertical-align: top; border: none;">
                <div>Signature: __________________________</div>
                <div><strong>Ghanshyam Jha</strong></div>
                <div>Roll No: 23016501000076</div>
              </td>
              <td style="width: 50%; padding: 8pt 4pt; vertical-align: top; border: none;">
                <div>Signature: __________________________</div>
                <div><strong>Abhishek Sharma</strong></div>
                <div>Roll No: 23016501000010</div>
              </td>
            </tr>
          </table>
          <div style="margin-top: 8pt;">Date: ________________________</div>
        </div>

        <div style="margin-top: 24pt; font-size: 11pt; line-height: 1.35;">
          <div style="font-weight: bold; margin-bottom: 6pt;">Approved By:</div>
          <br/>
          <div style="font-weight: bold;">Rahul Singh</div>
          <div>Head of Department</div>
          <div>Computer Science and Engineering</div>
          <div>KIT, KANPUR</div>
          <br/>
          <div>Signature: _________________________________________</div>
        </div>
      </div>
      <div class="page-footer">Page 2</div>
    </div>
    """
    pages.append(p2)

    # =========================================================================
    # PAGE 3: TABLE OF CONTENTS
    # =========================================================================
    p3 = """
    <div class="page" id="page-3">
      <div class="page-border"></div>
      <div style="padding-top: 8mm;">
        <h1 class="sec-title" style="margin-bottom: 12pt;">TABLE OF CONTENTS</h1>
        
        <table class="data-table" style="font-size: 11pt;">
          <thead>
            <tr style="background: #fafafa;">
              <th style="width: 12%; text-align: left;">No.</th>
              <th style="width: 70%; text-align: left;">Particulars</th>
              <th style="width: 18%; text-align: center;">Page</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>1.</td>
              <td>Introduction</td>
              <td style="text-align: center;">4</td>
            </tr>
            <tr>
              <td>2.</td>
              <td>Objectives and System Study</td>
              <td style="text-align: center;">5</td>
            </tr>
            <tr>
              <td>3.</td>
              <td>Requirement Analysis</td>
              <td style="text-align: center;">7</td>
            </tr>
            <tr>
              <td>4.</td>
              <td>System Architecture and Design</td>
              <td style="text-align: center;">8</td>
            </tr>
            <tr>
              <td>5.</td>
              <td>Module Description</td>
              <td style="text-align: center;">9</td>
            </tr>
            <tr>
              <td>6.</td>
              <td>Database Design</td>
              <td style="text-align: center;">11</td>
            </tr>
            <tr>
              <td>7.</td>
              <td>Implementation</td>
              <td style="text-align: center;">12</td>
            </tr>
            <tr>
              <td>8.</td>
              <td>Testing and Validation</td>
              <td style="text-align: center;">12</td>
            </tr>
            <tr>
              <td>9.</td>
              <td>Results, Benefits and Limitations</td>
              <td style="text-align: center;">13</td>
            </tr>
            <tr>
              <td>10.</td>
              <td>Future Scope and Conclusion</td>
              <td style="text-align: center;">14</td>
            </tr>
            <tr>
              <td>11.</td>
              <td>References and Appendix</td>
              <td style="text-align: center;">14</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="page-footer">Page 3</div>
    </div>
    """
    pages.append(p3)

    # =========================================================================
    # PAGE 4: 1. INTRODUCTION
    # =========================================================================
    p4 = """
    <div class="page" id="page-4">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">1. INTRODUCTION</h1>
        
        <h2 class="sub-title">1.1 Background</h2>
        <p>
          Personal computing workflows have expanded dramatically in scale and complexity. Modern knowledge workers, 
          engineers, and researchers routinely manage dozens of open applications, browser sessions, code workspaces, 
          and file systems. While cloud-hosted conversational Large Language Models (LLMs) demonstrate exceptional semantic reasoning, 
          they remain isolated within sandboxed browser tabs, acting as passive text advisors rather than proactive, hands-free 
          operating system actuators. Conversely, existing desktop robotic process automation (RPA) tools and macro scripts 
          are rigid, fragile to visual layout changes, and devoid of cognitive comprehension.
        </p>
        <p>
          PULSAR is engineered as a next-generation <strong>Hybrid Cloud-Edge Autonomous AI Assistant</strong> tailored specifically 
          for the Microsoft Windows ecosystem. PULSAR bridges high-reasoning cloud intelligence with resilient local edge execution. 
          It adopts Google Gemini (Gemini 2.5 Flash / 2.0 Pro) as its primary cloud cognitive brain for real-time multimodal reasoning, 
          broad knowledge synthesis, and dynamic code generation, while maintaining a fully functional, local 4.92 GB fine-tuned 
          quantized GGUF model (Llama 3.1 8B Instruct with speculative decoding and prompt caching), local Faster-Whisper, and 
          KittenTTS as a zero-latency, privacy-preserving offline fallback.
        </p>

        <h2 class="sub-title">1.2 Problem Statement</h2>
        <p>
          Contemporary AI assistants suffer from three critical architectural dilemmas:
        </p>
        <p>
          <em>First, the Cloud-Only Vulnerability:</em> Fully cloud-dependent assistants fail completely during intermittent network 
          outages, expose private local file hierarchies and screen states to external third parties, and incur substantial token costs. 
          <em>Second, the Edge-Only Performance Ceiling:</em> Solely offline CPU models struggle with complex multi-turn reasoning, 
          broad web research, and advanced computer vision tasks, suffering from prolonged CPU generation times. 
          <em>Third, the Actuation Void:</em> Neither paradigm possesses native, verifiable hooks into the host operating system 
          to manipulate running application windows, simulate spatial user interactions, or execute multi-step chained tasks autonomously.
        </p>
        <p>
          PULSAR solves this tripartite dilemma through an intelligent, network-aware hybrid routing fabric. Low-level OS control, 
          sensitive credential handling, and local file operations remain 100% on-device, while complex semantic reasoning, visual 
          screen comprehension, and web research scale transparently into Google Gemini's multimodal cloud pipeline.
        </p>

        <h2 class="sub-title">1.3 Need for the System</h2>
        <ul>
          <li><strong>Hybrid Brain Synergy:</strong> Harnesses Gemini 2.5 Flash for high-throughput cloud reasoning, with instant fallback to local quantized GGUF on network interruption.</li>
          <li><strong>Autonomous Multi-Agent Swarm:</strong> Incorporates 14 specialized domain agents built on AutoGen principles for automated multi-step task delegation.</li>
          <li><strong>Industry-Standard Tool Interoperability:</strong> Integrates the Model Context Protocol (MCP) to interact safely with filesystems, GitHub, and local databases.</li>
          <li><strong>Spatial Gesture & Vision Perception:</strong> Combines MediaPipe webcam hand-tracking (touchless cursor control) with Gemini Vision screen analysis.</li>
          <li><strong>Deterministic OS Actuation:</strong> Uses PyWin32, PyAutoGUI, and Windows Registry APIs with cryptographic PIN protection for sensitive actions.</li>
          <li><strong>Cognitive Episodic Memory:</strong> Employs SQLite FTS5 BM25 search coupled with 27 programmatic learning systems that adapt to user phrasing and Hinglish slang.</li>
        </ul>

        <h2 class="sub-title">1.4 Scope of the Project</h2>
        <p>
          The project scope encompasses an end-to-end operational software platform comprising: a reactive Iron Man JARVIS-inspired 
          HUD built with React 18, TypeScript, and Vite; a Python Flask 3.1 gateway with 11 modular REST/WebSocket service blueprints; 
          a 3-tier intent classification engine; streaming Faster-Whisper VAD audio ingestion; MediaPipe contactless hand-tracking; 
          14 domain-specific autonomous agents; and native Windows PyWebView desktop packaging.
        </p>
      </div>
      <div class="page-footer">Page 4</div>
    </div>
    """
    pages.append(p4)

    # =========================================================================
    # PAGE 5: 2. OBJECTIVES AND SYSTEM STUDY
    # =========================================================================
    p5 = """
    <div class="page" id="page-5">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">2. OBJECTIVES AND SYSTEM STUDY</h1>

        <h2 class="sub-title">2.1 Objectives</h2>
        <ol>
          <li>Engineer an intelligent, network-aware hybrid LLM routing engine toggling between Google Gemini (Cloud) and a local 4.92 GB fine-tuned GGUF model (Edge).</li>
          <li>Build an autonomous Multi-Agent Swarm with 14 specialized domain agents (Research, Writer, Analyst, Productivity, System) for complex goal decomposition.</li>
          <li>Implement the Model Context Protocol (MCP) client to expose standardized, sandboxed tool definitions across files, GitHub, and database backends.</li>
          <li>Develop a contactless spatial interaction subsystem using MediaPipe computer vision for webcam hand-gesture tracking and pinch-to-click actuation.</li>
          <li>Construct a zero-latency streaming voice pipeline combining RMS Energy-based VAD, Faster-Whisper transcription, Edge Neural TTS, and offline KittenTTS.</li>
          <li>Implement native Windows OS automation drivers using PyWin32, PyAutoGUI, and UI Automation for direct window, menu, and process control.</li>
          <li>Deploy a multi-tier intent router (Compiled Regex &rarr; Semantic Embeddings &rarr; Gemini Function Calling) ensuring sub-10ms dispatch for common queries.</li>
          <li>Establish a zero-dependency episodic memory system using SQLite FTS5 BM25 search, knowledge graph triples, and Ebbinghaus forgetting curve decay.</li>
          <li>Incorporate 27 continuous learning paradigms that dynamically adapt to user habits, linguistic intent drift, and colloquial Hinglish code-switching.</li>
          <li>Design an Iron Man JARVIS-themed cyberpunk desktop interface featuring pulsating Arc Reactor audio visualizers, telemetry graphs, and PyWebView wrapper.</li>
        </ol>

        <h2 class="sub-title">2.2 Existing System</h2>
        <p>
          Contemporary AI and automation solutions occupy fragmented silos: cloud conversational bots, rigid RPA software, and isolated 
          local LLM experiments. None offer a cohesive, multimodal, operating system-integrated companion.
        </p>

        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 22%;">Solution Category</th>
              <th style="width: 38%;">Representative Approach</th>
              <th style="width: 40%;">Architectural Limitations</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Cloud Chatbots</td>
              <td>ChatGPT, Claude Web, Gemini Web</td>
              <td>Sandboxed in browser; zero native OS control; zero offline resilience; privacy leakage.</td>
            </tr>
            <tr>
              <td>Desktop RPA / Macros</td>
              <td>AutoHotkey, UiPath, Power Automate</td>
              <td>Fragile coordinate-based scripts; zero cognitive reasoning; cannot handle natural language goals.</td>
            </tr>
            <tr>
              <td>Local-Only LLM Tools</td>
              <td>llama.cpp CLI, LM Studio</td>
              <td>Slow generation on consumer CPUs; limited multi-step reasoning; no multimodal vision or spatial gestures.</td>
            </tr>
            <tr>
              <td>OS Voice Assistants</td>
              <td>Cortana (Deprecated), Siri, Alexa</td>
              <td>Restricted to proprietary vendor ecosystems; shallow automation; rigid keyword command syntax.</td>
            </tr>
          </tbody>
        </table>

        <h2 class="sub-title">2.3 Proposed System</h2>
        <p>
          PULSAR synthesizes the cognitive power of cloud foundation models with the deterministic control and privacy of local OS execution. 
          By deploying a 3-tier routing fabric, PULSAR handles routine commands locally in under 10 milliseconds, delegates deep multimodal vision 
          and creative drafting to Google Gemini 2.5 Flash, and orchestrates 14 domain-specific AutoGen agents to execute complex workflows. 
          Should the internet connection drop, PULSAR seamlessly falls back to its local quantized GGUF core, ensuring perpetual operational reliability.
        </p>
      </div>
      <div class="page-footer">Page 5</div>
    </div>
    """
    pages.append(p5)

    # =========================================================================
    # PAGE 6: FIGURE 2.1 (HYBRID ORCHESTRATION WORKFLOW)
    # =========================================================================
    p6 = """
    <div class="page" id="page-6">
      <div class="page-border"></div>
      <div>
        <p style="margin-bottom: 5pt;">
          Figure 2.1 illustrates the end-to-end architectural workflow of PULSAR, highlighting the multimodal ingestion stream, 
          the 3-tier intent classification engine, the hybrid cloud-edge cognitive routing fabric, and the autonomous multi-agent execution pipeline.
        </p>

        <div class="fig-box">
          <svg width="575" height="745" viewBox="0 0 600 745" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <defs>
              <marker id="arr" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#2c3e50" />
              </marker>
              <marker id="arr-green" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#27ae60" />
              </marker>
              <marker id="arr-blue" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#2b6cb0" />
              </marker>
              <marker id="arr-red" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#c0392b" />
              </marker>
            </defs>

            <!-- GROUP 1: MULTIMODAL INGESTION & PERCEPTION -->
            <rect x="25" y="10" width="245" height="340" rx="9" fill="#f0f7ff" stroke="#3182ce" stroke-width="1.2" stroke-dasharray="4,3"/>
            <text x="38" y="28" font-size="10.5" font-weight="bold" fill="#2b6cb0" letter-spacing="0.5">MULTIMODAL SENSORY INGESTION</text>

            <rect x="75" y="44" width="145" height="28" rx="14" fill="#1a365d"/>
            <text x="147" y="62" font-size="9.5" font-weight="bold" fill="#ffffff" text-anchor="middle">User Multimodal Input</text>

            <line x1="147" y1="72" x2="147" y2="88" stroke="#2c3e50" stroke-width="1.4" marker-end="url(#arr)"/>

            <rect x="42" y="88" width="210" height="42" rx="5" fill="#ffffff" stroke="#3182ce" stroke-width="1.1"/>
            <text x="147" y="104" font-size="9" font-weight="bold" fill="#2d3748" text-anchor="middle">Streaming VAD & Audio Stream</text>
            <text x="147" y="118" font-size="8" fill="#4a5568" text-anchor="middle">700ms RMS Cutoff + In-Memory BytesIO</text>

            <line x1="147" y1="130" x2="147" y2="146" stroke="#2c3e50" stroke-width="1.4" marker-end="url(#arr)"/>

            <rect x="42" y="146" width="210" height="42" rx="5" fill="#e6fffa" stroke="#319795" stroke-width="1.1"/>
            <text x="147" y="162" font-size="9" font-weight="bold" fill="#234e52" text-anchor="middle">Sensory Preprocessors</text>
            <text x="147" y="176" font-size="8" fill="#285e61" text-anchor="middle">Faster-Whisper STT | MediaPipe Hands | OCR</text>

            <line x1="147" y1="188" x2="147" y2="204" stroke="#2c3e50" stroke-width="1.4" marker-end="url(#arr)"/>

            <!-- 3-TIER INTENT CLASSIFIER -->
            <rect x="42" y="204" width="210" height="64" rx="5" fill="#ffffff" stroke="#805ad5" stroke-width="1.2"/>
            <text x="147" y="220" font-size="9" font-weight="bold" fill="#553c9a" text-anchor="middle">3-Tier Intent Router</text>
            <text x="147" y="233" font-size="7.5" fill="#4a5568" text-anchor="middle">Tier 1: Regex Match (~0ms)</text>
            <text x="147" y="246" font-size="7.5" fill="#4a5568" text-anchor="middle">Tier 2: Semantic Embeddings (~12ms)</text>
            <text x="147" y="259" font-size="7.5" fill="#4a5568" text-anchor="middle">Tier 3: Gemini Function Calling</text>

            <line x1="147" y1="268" x2="147" y2="288" stroke="#2c3e50" stroke-width="1.4" marker-end="url(#arr)"/>

            <rect x="52" y="288" width="190" height="46" rx="5" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.1"/>
            <text x="147" y="304" font-size="8.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Central Agent Dispatcher</text>
            <text x="147" y="318" font-size="7.5" fill="#4a5568" text-anchor="middle">Chained Goal Planning & DAG Synthesis</text>

            <!-- GROUP 2: HYBRID COGNITIVE BRAIN -->
            <rect x="315" y="10" width="260" height="340" rx="9" fill="#f0fff4" stroke="#38a169" stroke-width="1.2" stroke-dasharray="4,3"/>
            <text x="328" y="28" font-size="10.5" font-weight="bold" fill="#276749" letter-spacing="0.5">HYBRID CLOUD-EDGE REASONING</text>

            <path d="M 242 311 L 285 311 L 285 64 L 335 64" fill="none" stroke="#2c3e50" stroke-width="1.4" marker-end="url(#arr)"/>

            <polygon points="445,46 515,68 445,90 375,68" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="445" y="66" font-size="8.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Network</text>
            <text x="445" y="76" font-size="7.5" fill="#7b341e" text-anchor="middle">Available?</text>

            <!-- Yes: Left side (Cloud Gemini) -->
            <path d="M 375 68 L 360 68 L 360 100" fill="none" stroke="#27ae60" stroke-width="1.4" marker-end="url(#arr-green)"/>
            <text x="330" y="63" font-size="7.5" font-weight="bold" fill="#27ae60">Yes (Cloud)</text>

            <rect x="325" y="100" width="115" height="52" rx="4" fill="#ffffff" stroke="#27ae60" stroke-width="1.2"/>
            <text x="382" y="115" font-size="8" font-weight="bold" fill="#22543d" text-anchor="middle">Google Gemini</text>
            <text x="382" y="126" font-size="7" fill="#22543d" text-anchor="middle">2.5 Flash / 2.0 Pro</text>
            <text x="382" y="137" font-size="6.5" fill="#4a5568" text-anchor="middle">Cloud Reasoning & Vision</text>
            <text x="382" y="146" font-size="6.5" fill="#4a5568" text-anchor="middle">Presence & Mood Sensing</text>

            <!-- No: Right side (Local GGUF) -->
            <path d="M 515 68 L 530 68 L 530 100" fill="none" stroke="#c0392b" stroke-width="1.4" marker-end="url(#arr-red)"/>
            <text x="560" y="63" font-size="7.5" font-weight="bold" fill="#c0392b">No (Offline)</text>

            <rect x="450" y="100" width="115" height="52" rx="4" fill="#ffffff" stroke="#c0392b" stroke-width="1.2"/>
            <text x="507" y="115" font-size="8" font-weight="bold" fill="#742a2a" text-anchor="middle">Local GGUF Core</text>
            <text x="507" y="126" font-size="7" fill="#742a2a" text-anchor="middle">Llama 3 8B (4.92GB)</text>
            <text x="507" y="137" font-size="6.5" fill="#4a5568" text-anchor="middle">Speculative Cache AVX2</text>
            <text x="507" y="146" font-size="6.5" fill="#4a5568" text-anchor="middle">Zero-Leakage Fallback</text>

            <!-- Converge to Swarm -->
            <path d="M 382 152 L 382 175 L 445 175" fill="none" stroke="#2c3e50" stroke-width="1.4"/>
            <path d="M 507 152 L 507 175 L 445 175" fill="none" stroke="#2c3e50" stroke-width="1.4"/>
            <line x1="445" y1="175" x2="445" y2="190" stroke="#2c3e50" stroke-width="1.4" marker-end="url(#arr)"/>

            <!-- 14-AGENT SWARM -->
            <rect x="330" y="190" width="230" height="54" rx="5" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="445" y="206" font-size="9" font-weight="bold" fill="#2b6cb0" text-anchor="middle">14-Agent AutoGen Swarm</text>
            <text x="445" y="219" font-size="7.5" fill="#4a5568" text-anchor="middle">Deep Research | Writer | Analyst | Database</text>
            <text x="445" y="230" font-size="7.5" fill="#4a5568" text-anchor="middle">Productivity | Student | Media | Autonomous</text>
            <text x="445" y="240" font-size="7" fill="#718096" text-anchor="middle">Dynamic DAG Task Negotiation</text>

            <line x1="445" y1="244" x2="445" y2="262" stroke="#2c3e50" stroke-width="1.4" marker-end="url(#arr)"/>

            <rect x="340" y="262" width="210" height="32" rx="4" fill="#ffffff" stroke="#38a169" stroke-width="1.1"/>
            <text x="445" y="276" font-size="8" font-weight="bold" fill="#276749" text-anchor="middle">Model Context Protocol (MCP)</text>
            <text x="445" y="287" font-size="7" fill="#4a5568" text-anchor="middle">JSON-RPC Sandboxed Tool Execution</text>

            <!-- GROUP 3: OS ACTUATION & VERIFICATION -->
            <rect x="25" y="375" width="550" height="330" rx="9" fill="#faf5ff" stroke="#805ad5" stroke-width="1.2" stroke-dasharray="4,3"/>
            <text x="38" y="394" font-size="10.5" font-weight="bold" fill="#6b46c1" letter-spacing="0.5">DETERMINISTIC OS ACTUATION, MEMORY & SELF-HEALING</text>

            <path d="M 445 340 L 445 365 L 300 365 L 300 410" fill="none" stroke="#2c3e50" stroke-width="1.4" marker-end="url(#arr)"/>

            <!-- PIN SECURITY GATE -->
            <polygon points="300,410 380,432 300,454 220,432" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="300" y="429" font-size="8.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Privileged Action?</text>
            <text x="300" y="440" font-size="7.5" fill="#7b341e" text-anchor="middle">(File Delete / Kill / Reg)</text>

            <line x1="380" y1="432" x2="435" y2="432" stroke="#dd6b20" stroke-width="1.4" marker-end="url(#arr)"/>
            <text x="395" y="425" font-size="8" font-weight="bold" fill="#dd6b20">Yes</text>

            <rect x="435" y="418" width="125" height="28" rx="4" fill="#feebc8" stroke="#c05621" stroke-width="1.1"/>
            <text x="497" y="431" font-size="8" font-weight="bold" fill="#7b341e" text-anchor="middle">Verify PIN_HASH</text>
            <text x="497" y="441" font-size="6.5" fill="#7b341e" text-anchor="middle">Salted SHA-256 Gate</text>

            <line x1="300" y1="454" x2="300" y2="475" stroke="#27ae60" stroke-width="1.4" marker-end="url(#arr-green)"/>
            <text x="306" y="465" font-size="8" font-weight="bold" fill="#27ae60">No</text>
            <path d="M 497 446 L 497 475 L 300 475" fill="none" stroke="#27ae60" stroke-width="1.4"/>

            <!-- EXECUTION ENGINE -->
            <rect x="180" y="480" width="240" height="42" rx="5" fill="#ffffff" stroke="#805ad5" stroke-width="1.2"/>
            <text x="300" y="497" font-size="9" font-weight="bold" fill="#2d3748" text-anchor="middle">Windows Automation Engine</text>
            <text x="300" y="510" font-size="8" fill="#553c9a" text-anchor="middle">PyWin32 | PyAutoGUI | PyCAW | UIAutomation</text>

            <line x1="300" y1="522" x2="300" y2="542" stroke="#2c3e50" stroke-width="1.4" marker-end="url(#arr)"/>

            <polygon points="300,542 375,565 300,588 225,565" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="300" y="562" font-size="8.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Action</text>
            <text x="300" y="573" font-size="7.5" fill="#7b341e" text-anchor="middle">Verified?</text>

            <!-- Self-Healing Loop -->
            <path d="M 225 565 L 120 565 L 120 501 L 180 501" fill="none" stroke="#c0392b" stroke-width="1.4" marker-end="url(#arr-red)"/>
            <text x="145" y="558" font-size="8" font-weight="bold" fill="#c0392b">No: Self-Heal</text>
            <text x="145" y="546" font-size="7" fill="#742a2a">(OCR Traceback Recalibrate)</text>

            <line x1="300" y1="588" x2="300" y2="608" stroke="#27ae60" stroke-width="1.4" marker-end="url(#arr-green)"/>
            <text x="306" y="599" font-size="8" font-weight="bold" fill="#27ae60">Yes</text>

            <!-- DUAL COMPLETION -->
            <rect x="55" y="608" width="225" height="44" rx="5" fill="#e6fffa" stroke="#319795" stroke-width="1.1"/>
            <text x="167" y="624" font-size="8.5" font-weight="bold" fill="#234e52" text-anchor="middle">SQLite FTS5 Episodic Memory</text>
            <text x="167" y="635" font-size="7.5" fill="#285e61" text-anchor="middle">27 Paradigms: Active Learning, Hinglish</text>
            <text x="167" y="645" font-size="7.5" fill="#285e61" text-anchor="middle">Adaptation & Ebbinghaus Curve Decay</text>

            <rect x="320" y="608" width="225" height="44" rx="5" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.1"/>
            <text x="432" y="624" font-size="8.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">JARVIS Cyberpunk HUD Update</text>
            <text x="432" y="635" font-size="7.5" fill="#4a5568" text-anchor="middle">Edge Neural TTS / KittenTTS Audio +</text>
            <text x="432" y="645" font-size="7.5" fill="#4a5568" text-anchor="middle">Arc Reactor Pulse & Telemetry Refresh</text>

            <line x1="167" y1="652" x2="167" y2="670" stroke="#2c3e50" stroke-width="1.4"/>
            <line x1="432" y1="652" x2="432" y2="670" stroke="#2c3e50" stroke-width="1.4"/>
            <line x1="167" y1="670" x2="432" y2="670" stroke="#2c3e50" stroke-width="1.4"/>
            <line x1="300" y1="670" x2="300" y2="685" stroke="#2c3e50" stroke-width="1.4" marker-end="url(#arr)"/>

            <rect x="235" y="685" width="130" height="26" rx="13" fill="#1a365d"/>
            <text x="300" y="702" font-size="9.5" font-weight="bold" fill="#ffffff" text-anchor="middle">Execution Complete</text>
          </svg>
          <div class="fig-cap">Figure 2.1: End-to-end hybrid cloud-edge orchestration and autonomous execution workflow of PULSAR</div>
        </div>
      </div>
      <div class="page-footer">Page 6</div>
    </div>
    """
    pages.append(p6)

    # =========================================================================
    # PAGE 7: 3. REQUIREMENT ANALYSIS
    # =========================================================================
    p7 = """
    <div class="page" id="page-7">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">3. REQUIREMENT ANALYSIS</h1>

        <h2 class="sub-title">3.1 Functional Requirements</h2>
        <ul>
          <li><strong>Hybrid LLM Cognition:</strong> Default to Google Gemini 2.5 Flash for high-speed cloud reasoning, with automated seamless fallback to local quantized GGUF on network loss.</li>
          <li><strong>Streaming Speech Ingestion:</strong> Continuous microphone streaming using RMS energy-based Voice Activity Detection (VAD) with zero-disk-IO Faster-Whisper transcription.</li>
          <li><strong>Contactless Spatial Interaction:</strong> Real-time MediaPipe hand-tracking via webcam to control an on-screen spatial cursor and execute pinch-to-click GUI events.</li>
          <li><strong>Multimodal Computer Vision:</strong> High-resolution screen frame capture and live webcam presence/emotion assessment powered by Google Gemini Vision.</li>
          <li><strong>Autonomous Multi-Agent Swarm:</strong> Dynamic task planning and execution across 14 specialized domain agents (Research, Writer, Analyst, Productivity, System).</li>
          <li><strong>Model Context Protocol (MCP):</strong> Sandboxed, standard tool protocol integrating local filesystem access, GitHub, PostgreSQL, and SQLite databases.</li>
          <li><strong>Deterministic OS Automation:</strong> Direct Windows manipulation via PyWin32, PyAutoGUI, and UI Automation (window focus, keystrokes, application launch).</li>
          <li><strong>3-Tier Intent Classification:</strong> Rapid intent parsing transitioning across Regex patterns, SentenceTransformer embeddings, and Gemini Function Calling.</li>
          <li><strong>Cognitive Episodic Memory:</strong> Persistent conversational retrieval using SQLite FTS5 BM25 search, knowledge graph triples, and Ebbinghaus memory fading.</li>
          <li><strong>Cryptographic Authorization Gate:</strong> Salted SHA-256 PIN verification for privileged system actions (file deletion, process termination, registry edits).</li>
        </ul>

        <h2 class="sub-title">3.2 Non-Functional Requirements</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 24%;">Requirement</th>
              <th style="width: 76%;">Engineering Implementation & Validation Target</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Availability & Resilience</td>
              <td>Hybrid architecture guarantees 100% operational uptime for local OS automation even when disconnected from the internet.</td>
            </tr>
            <tr>
              <td>Voice & Intent Latency</td>
              <td>Sub-250ms streaming STT latency; sub-10ms intent dispatch for cached/regex commands; under 1.2s cloud token turnaround.</td>
            </tr>
            <tr>
              <td>Security & Data Privacy</td>
              <td>Salted SHA-256 PIN hashing; AES-encrypted database storage; automated NER scrubbing of sensitive PII before cloud dispatch.</td>
            </tr>
            <tr>
              <td>Memory & Compute Bounds</td>
              <td>Local GGUF footprint strictly bounded under 6.5 GB RAM via 8-bit KV caching and speculative decoding on Intel Core Ultra / x64 CPUs.</td>
            </tr>
            <tr>
              <td>Visual Ergonomics</td>
              <td>Iron Man JARVIS-inspired HUD with pulsing Arc Reactor audio visualizers, glassmorphism, and frameless PyWebView container.</td>
            </tr>
            <tr>
              <td>Linguistic Extensibility</td>
              <td>Dynamic adaptation to bilingual code-switching, Hinglish slang, and user-specific vocabulary via continuous learning routines.</td>
            </tr>
          </tbody>
        </table>

        <h2 class="sub-title">3.3 Hardware and Software Environment Specifications</h2>
        <p>
          <strong>Hardware Specifications:</strong> Intel Core i5/i7 (8th Gen+) or AMD Ryzen 5/7 quad-core processor (optimized for Intel Core Ultra 7 architecture with physical P-core pinning); minimum 8 GB of RAM (16 GB recommended for concurrent local GGUF execution); 20 GB available SSD storage; HD webcam (for MediaPipe spatial tracking and presence sensing); standard microphone and audio output.
        </p>
        <p>
          <strong>Software Specifications:</strong> Microsoft Windows 10/11 64-bit; Python 3.10+ runtime; Node.js 18+ and npm; Google Gemini API SDK (`google-genai` / `google-generativeai`); `llama-cpp-python` with AVX2 vector optimizations; MediaPipe vision tasks; Tesseract-OCR 5; SQLite3; modern Chromium engine (PyWebView); Git version control.
        </p>
      </div>
      <div class="page-footer">Page 7</div>
    </div>
    """
    pages.append(p7)

    # =========================================================================
    # PAGE 8: 4. SYSTEM ARCHITECTURE AND DESIGN
    # =========================================================================
    p8 = """
    <div class="page" id="page-8">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">4. SYSTEM ARCHITECTURE AND DESIGN</h1>

        <h2 class="sub-title">4.1 Architectural Overview</h2>
        <p>
          PULSAR follows a 5-tier, edge-native micro-service architecture that cleanly isolates client rendering, API routing, 
          cognitive intelligence, multimodal sensory processing, and persistent data storage. The frontend is a React 18 single-page 
          application wrapped in a frameless PyWebView native window, communicating with a high-throughput Python Flask 3.1 
          gateway via bidirectional WebSockets and REST endpoints.
        </p>

        <div class="fig-box">
          <svg width="560" height="345" viewBox="0 0 580 355" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <!-- Tier 1: Client Layer -->
            <rect x="15" y="10" width="550" height="54" rx="7" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="28" y="27" font-size="9.5" font-weight="bold" fill="#2b6cb0">1. JARVIS CLIENT HUD</text>
            <rect x="150" y="20" width="195" height="34" rx="4" fill="#ffffff" stroke="#3182ce" stroke-width="1"/>
            <text x="247" y="34" font-size="8" font-weight="bold" fill="#2d3748" text-anchor="middle">React 18 + Vite + Tailwind</text>
            <text x="247" y="45" font-size="7" fill="#718096" text-anchor="middle">Arc Reactor Visualizer | Telemetry | Chat</text>
            <rect x="355" y="20" width="195" height="34" rx="4" fill="#ffffff" stroke="#3182ce" stroke-width="1"/>
            <text x="452" y="34" font-size="8" font-weight="bold" fill="#2d3748" text-anchor="middle">MediaPipe Spatial Cursor</text>
            <text x="452" y="45" font-size="7" fill="#718096" text-anchor="middle">Webcam Hand-Tracking | PyWebView</text>

            <line x1="290" y1="64" x2="290" y2="78" stroke="#2c3e50" stroke-width="1.3" stroke-dasharray="3,3"/>

            <!-- Tier 2: Gateway Layer -->
            <rect x="15" y="78" width="550" height="54" rx="7" fill="#f7fafc" stroke="#4a5568" stroke-width="1.2"/>
            <text x="28" y="95" font-size="9.5" font-weight="bold" fill="#2d3748">2. API GATEWAY</text>
            <rect x="135" y="88" width="130" height="34" rx="4" fill="#ffffff" stroke="#4a5568" stroke-width="1"/>
            <text x="200" y="102" font-size="8" font-weight="bold" fill="#2d3748" text-anchor="middle">Flask 3.1 REST Server</text>
            <text x="200" y="112" font-size="6.5" fill="#718096" text-anchor="middle">11 Modular Service Blueprints</text>
            <rect x="275" y="88" width="130" height="34" rx="4" fill="#ffffff" stroke="#4a5568" stroke-width="1"/>
            <text x="340" y="102" font-size="8" font-weight="bold" fill="#2d3748" text-anchor="middle">Socket.IO WebSockets</text>
            <text x="340" y="112" font-size="6.5" fill="#718096" text-anchor="middle">Realtime Streaming & Presence</text>
            <rect x="415" y="88" width="135" height="34" rx="4" fill="#ffffff" stroke="#4a5568" stroke-width="1"/>
            <text x="482" y="102" font-size="8" font-weight="bold" fill="#2d3748" text-anchor="middle">Security & PIN Gate</text>
            <text x="482" y="112" font-size="6.5" fill="#718096" text-anchor="middle">Salted SHA-256 Verification</text>

            <line x1="290" y1="132" x2="290" y2="146" stroke="#2c3e50" stroke-width="1.3"/>

            <!-- Tier 3: Cognitive & Multi-Agent Layer -->
            <rect x="15" y="146" width="550" height="60" rx="7" fill="#f0fff4" stroke="#38a169" stroke-width="1.2"/>
            <text x="28" y="163" font-size="9.5" font-weight="bold" fill="#276749">3. HYBRID COGNITION</text>
            <rect x="140" y="154" width="135" height="42" rx="4" fill="#ffffff" stroke="#38a169" stroke-width="1"/>
            <text x="207" y="168" font-size="8" font-weight="bold" fill="#276749" text-anchor="middle">Google Gemini Cloud</text>
            <text x="207" y="178" font-size="6.5" fill="#718096" text-anchor="middle">Gemini 2.5 Flash / 2.0 Pro</text>
            <text x="207" y="188" font-size="6.5" fill="#718096" text-anchor="middle">Multimodal & Deep Reasoning</text>
            <rect x="285" y="154" width="135" height="42" rx="4" fill="#ffffff" stroke="#38a169" stroke-width="1"/>
            <text x="352" y="168" font-size="8" font-weight="bold" fill="#c0392b" text-anchor="middle">Local GGUF Fallback</text>
            <text x="352" y="178" font-size="6.5" fill="#718096" text-anchor="middle">Llama 3 8B Q4 (4.92 GB)</text>
            <text x="352" y="188" font-size="6.5" fill="#718096" text-anchor="middle">Speculative Cache on AVX2</text>
            <rect x="430" y="154" width="120" height="42" rx="4" fill="#ffffff" stroke="#38a169" stroke-width="1"/>
            <text x="490" y="168" font-size="8" font-weight="bold" fill="#2b6cb0" text-anchor="middle">14 AutoGen Agents</text>
            <text x="490" y="178" font-size="6.5" fill="#718096" text-anchor="middle">Deep Research, Writer,</text>
            <text x="490" y="188" font-size="6.5" fill="#718096" text-anchor="middle">Productivity, Analyst Swarm</text>

            <line x1="290" y1="206" x2="290" y2="220" stroke="#2c3e50" stroke-width="1.3"/>

            <!-- Tier 4: Perception & OS Actuation Layer -->
            <rect x="15" y="220" width="550" height="54" rx="7" fill="#faf5ff" stroke="#805ad5" stroke-width="1.2"/>
            <text x="28" y="237" font-size="9.5" font-weight="bold" fill="#6b46c1">4. PERCEPTION & OS</text>
            <rect x="145" y="228" width="125" height="34" rx="4" fill="#ffffff" stroke="#805ad5" stroke-width="1"/>
            <text x="207" y="242" font-size="8" font-weight="bold" fill="#2d3748" text-anchor="middle">Voice Pipeline</text>
            <text x="207" y="253" font-size="6.5" fill="#718096" text-anchor="middle">Faster-Whisper + Edge TTS</text>
            <rect x="280" y="228" width="130" height="34" rx="4" fill="#ffffff" stroke="#805ad5" stroke-width="1"/>
            <text x="345" y="242" font-size="8" font-weight="bold" fill="#2d3748" text-anchor="middle">Vision & OCR</text>
            <text x="345" y="253" font-size="6.5" fill="#718096" text-anchor="middle">Gemini Vision + Tesseract 5</text>
            <rect x="420" y="228" width="130" height="34" rx="4" fill="#ffffff" stroke="#805ad5" stroke-width="1"/>
            <text x="485" y="242" font-size="8" font-weight="bold" fill="#2d3748" text-anchor="middle">Win32 Actuation</text>
            <text x="485" y="253" font-size="6.5" fill="#718096" text-anchor="middle">PyWin32, PyAutoGUI, MCP</text>

            <line x1="290" y1="274" x2="290" y2="288" stroke="#2c3e50" stroke-width="1.3"/>

            <!-- Tier 5: Persistence & Memory Layer -->
            <rect x="15" y="288" width="550" height="52" rx="7" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="28" y="306" font-size="9" font-weight="bold" fill="#c05621">5. DATA & MEMORY</text>
            <rect x="155" y="296" width="190" height="32" rx="4" fill="#ffffff" stroke="#dd6b20" stroke-width="1"/>
            <text x="250" y="310" font-size="8" font-weight="bold" fill="#2d3748" text-anchor="middle">SQLite Cluster (8 Databases)</text>
            <text x="250" y="320" font-size="6.5" fill="#718096" text-anchor="middle">memory.db (FTS5 BM25), chat, learning</text>
            <rect x="355" y="296" width="195" height="32" rx="4" fill="#ffffff" stroke="#dd6b20" stroke-width="1"/>
            <text x="452" y="310" font-size="8" font-weight="bold" fill="#2d3748" text-anchor="middle">27 Learning Systems & Config</text>
            <text x="452" y="320" font-size="6.5" fill="#718096" text-anchor="middle">Hinglish Intent Drift, Ebbinghaus Decay</text>
          </svg>
          <div class="fig-cap">Figure 4.1: High-level 5-tier hybrid system architecture of PULSAR</div>
        </div>

        <h2 class="sub-title">4.2 Major Components & Security</h2>
        <p>
          The architecture cleanly separates responsibilities: the React UI handles high-framerate visual rendering and gesture tracking; 
          the Flask gateway routes requests to asynchronous background worker pools; the hybrid cognitive core dynamically allocates tasks 
          between Google Gemini and local GGUF models; and the Win32 automation engine safely manipulates host applications. Security is 
          enforced through a salted SHA-256 PIN challenge on privileged commands, encrypted local storage, and automated PII sanitization.
        </p>
      </div>
      <div class="page-footer">Page 8</div>
    </div>
    """
    pages.append(p8)

    # =========================================================================
    # PAGE 9: 5. MODULE DESCRIPTION (PART 1)
    # =========================================================================
    p9 = """
    <div class="page" id="page-9">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">5. MODULE DESCRIPTION</h1>

        <h2 class="sub-title">5.1 Hybrid Cognitive Reasoning Engine</h2>
        <p>
          The core intelligence of PULSAR is powered by a network-aware dual-engine architecture:
        </p>
        <p>
          <strong>Cloud Foundation Brain:</strong> When an active internet connection is detected, PULSAR defaults to Google Gemini 
          (Gemini 2.5 Flash / 2.0 Pro) via the `google-genai` and `google-generativeai` SDKs. Gemini delivers rapid token generation, 
          deep multi-step reasoning, natural conversational personality, and multimodal image understanding.
        </p>
        <p>
          <strong>Resilient Local GGUF Core:</strong> If network connectivity is interrupted, the system automatically falls back 
          to a 4.92 GB fine-tuned Llama 3 8B Instruct model (`pulsar-final-q4_k_m.gguf`) managed by `llama-cpp-python`. This local engine 
          incorporates Intel Core Ultra 7 CPU optimizations, restricting inference to 6 physical P-cores to avoid L3 cache thrashing, 
          `use_mlock=True` to prevent pagefile swapping, speculative prompt-lookup decoding for 1.8x acceleration, and 8-bit KV caching.
        </p>

        <h2 class="sub-title">5.2 Three-Tier Intent Routing Engine</h2>
        <p>
          To achieve near-instantaneous execution without unnecessary API overhead, user commands traverse a 3-tier classifier:
        </p>
        <ul>
          <li><strong>Tier 1 (Regex Engine, ~0ms):</strong> Evaluates pre-compiled regular expressions for deterministic desktop commands (volume control, application launching, system stats).</li>
          <li><strong>Tier 2 (Semantic Embedding Matcher, ~12ms):</strong> Uses local sentence embeddings to resolve fuzzy or paraphrased intents against an indexed database of system actions.</li>
          <li><strong>Tier 3 (Gemini Function Calling):</strong> Ambiguous or complex compound requests are processed by Gemini's native function-calling declarations to extract structured JSON parameters.</li>
        </ul>

        <h2 class="sub-title">5.3 Authentication & Privileged Access Module</h2>
        <p>
          Any command that deletes files, kills running system processes, or modifies the Windows Registry must pass the PIN Security Gate.
        </p>

        <div class="fig-box">
          <svg width="540" height="195" viewBox="0 0 540 205" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <defs>
              <marker id="arr9" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
                <polygon points="0 0, 7 2.5, 0 5" fill="#2c3e50" />
              </marker>
            </defs>

            <rect x="180" y="6" width="180" height="24" rx="12" fill="#1a365d"/>
            <text x="270" y="22" font-size="8.5" font-weight="bold" fill="#ffffff" text-anchor="middle">User Action Ingestion</text>

            <line x1="270" y1="30" x2="270" y2="46" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr9)"/>

            <polygon points="270,46 350,65 270,84 190,65" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="270" y="63" font-size="8" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Privileged Action?</text>
            <text x="270" y="72" font-size="7" fill="#2b6cb0" text-anchor="middle">(File Delete / Kill / Reg)</text>

            <!-- Standard Branch -->
            <line x1="190" y1="65" x2="95" y2="65" stroke="#27ae60" stroke-width="1.3"/>
            <line x1="95" y1="65" x2="95" y2="152" stroke="#27ae60" stroke-width="1.3"/>
            <line x1="95" y1="152" x2="185" y2="152" stroke="#27ae60" stroke-width="1.3" marker-end="url(#arr9)"/>
            <text x="135" y="59" font-size="7.5" font-weight="bold" fill="#27ae60">No (Standard)</text>

            <!-- Elevated Branch -->
            <line x1="270" y1="84" x2="270" y2="98" stroke="#dd6b20" stroke-width="1.3" marker-end="url(#arr9)"/>
            <text x="276" y="93" font-size="7.5" font-weight="bold" fill="#dd6b20">Yes</text>

            <rect x="190" y="98" width="160" height="26" rx="4" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="270" y="110" font-size="7.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Prompt PIN Challenge</text>
            <text x="270" y="120" font-size="6.5" fill="#7b341e" text-anchor="middle">Hash against Salted PIN_HASH</text>

            <line x1="270" y1="124" x2="270" y2="136" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr9)"/>

            <polygon points="270,136 335,151 270,166 205,151" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.1"/>
            <text x="270" y="154" font-size="7" font-weight="bold" fill="#7b341e" text-anchor="middle">Hash Match?</text>

            <!-- Failed -->
            <line x1="335" y1="151" x2="410" y2="151" stroke="#c0392b" stroke-width="1.3" marker-end="url(#arr9)"/>
            <text x="365" y="145" font-size="7" font-weight="bold" fill="#c0392b">No</text>
            <rect x="410" y="138" width="110" height="26" rx="4" fill="#fff5f5" stroke="#e53e3e" stroke-width="1"/>
            <text x="465" y="150" font-size="7.5" font-weight="bold" fill="#c53030" text-anchor="middle">403 Forbidden</text>
            <text x="465" y="159" font-size="6.5" fill="#c53030" text-anchor="middle">Security Alert Logged</text>

            <!-- Success -->
            <line x1="270" y1="166" x2="270" y2="180" stroke="#27ae60" stroke-width="1.3" marker-end="url(#arr9)"/>
            <text x="276" y="175" font-size="7" font-weight="bold" fill="#27ae60">Yes</text>

            <rect x="185" y="180" width="170" height="24" rx="4" fill="#e6fffa" stroke="#319795" stroke-width="1.2"/>
            <text x="270" y="196" font-size="8" font-weight="bold" fill="#234e52" text-anchor="middle">Execute Privileged Win32 Action</text>
          </svg>
          <div class="fig-cap">Figure 5.1: Salted PIN elevation challenge and privileged execution gate</div>
        </div>

        <h2 class="sub-title">5.4 Multimodal Perception & Spatial Interaction</h2>
        <p>
          PULSAR ingests sensory signals across three primary modalities:
        </p>
        <ul>
          <li><strong>Streaming Audio Pipeline:</strong> Ingests live audio via `LiveVoiceStreamer`, utilizing RMS energy-based VAD with a 700ms cutoff to feed in-memory `io.BytesIO` buffers directly into Faster-Whisper. Audio responses synthesize via Microsoft Edge Neural TTS (13 distinct voices) or local KittenTTS.</li>
          <li><strong>Gemini Computer Vision:</strong> Evaluates active window frames and webcam video via `gemini-1.5-flash` for contextual scene analysis, error dialog inspection, and periodic user presence/mood monitoring.</li>
          <li><strong>Contactless Spatial Cursor:</strong> MediaPipe Hands tracks hand landmarks from the webcam feed, projecting a floating pointer across the screen where finger-pinch gestures simulate physical mouse clicks.</li>
        </ul>
      </div>
      <div class="page-footer">Page 9</div>
    </div>
    """
    pages.append(p9)

    # =========================================================================
    # PAGE 10: 5. MODULE DESCRIPTION (PART 2)
    # =========================================================================
    p10 = """
    <div class="page" id="page-10">
      <div class="page-border"></div>
      <div>
        <h2 class="sub-title" style="margin-top: 0;">5.5 AutoGen Multi-Agent Swarm (14 Specialized Agents)</h2>
        <p>
          To autonomously execute multi-step user requests, PULSAR deploys a swarm of 14 specialized, lazy-loaded agents 
          built using the AutoGen (`autogen-agentchat`) framework. Governed by a central Dispatcher and TaskScheduler, 
          the swarm collaborates over structured Directed Acyclic Graphs (DAGs):
        </p>

        <div class="fig-box">
          <svg width="550" height="235" viewBox="0 0 560 245" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <defs>
              <marker id="arr10" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
                <polygon points="0 0, 7 2.5, 0 5" fill="#2c3e50" />
              </marker>
              <marker id="arr-red10" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
                <polygon points="0 0, 7 2.5, 0 5" fill="#c0392b" />
              </marker>
            </defs>

            <rect x="180" y="6" width="200" height="24" rx="12" fill="#1a365d"/>
            <text x="280" y="21" font-size="8.5" font-weight="bold" fill="#ffffff" text-anchor="middle">Complex User Goal Ingested</text>

            <line x1="280" y1="30" x2="280" y2="46" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr10)"/>

            <rect x="160" y="46" width="240" height="28" rx="4" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="280" y="59" font-size="8" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Task Chain Orchestrator (DAG Planner)</text>
            <text x="280" y="69" font-size="7" fill="#4a5568" text-anchor="middle">Breaks complex goal into sequential dependencies</text>

            <line x1="280" y1="74" x2="280" y2="90" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr10)"/>

            <rect x="150" y="90" width="260" height="34" rx="4" fill="#f0fff4" stroke="#38a169" stroke-width="1.2"/>
            <text x="280" y="103" font-size="8" font-weight="bold" fill="#276749" text-anchor="middle">Swarm Allocation (14 AutoGen Agents)</text>
            <text x="280" y="113" font-size="7" fill="#4a5568" text-anchor="middle">Deep Research | Writer | Analyst | Productivity | Student</text>
            <text x="280" y="122" font-size="6.5" fill="#4a5568" text-anchor="middle">Database | Web | Media | Communication | Autonomous</text>

            <line x1="280" y1="124" x2="280" y2="138" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr10)"/>

            <rect x="160" y="138" width="240" height="28" rx="4" fill="#faf5ff" stroke="#805ad5" stroke-width="1.2"/>
            <text x="280" y="150" font-size="8" font-weight="bold" fill="#6b46c1" text-anchor="middle">Tool & MCP Execution Layer</text>
            <text x="280" y="160" font-size="7" fill="#4a5568" text-anchor="middle">Filesystem, PyWin32, GitHub, Database, Office</text>

            <line x1="280" y1="166" x2="280" y2="180" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr10)"/>

            <polygon points="280,180 345,196 280,212 215,196" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.1"/>
            <text x="280" y="194" font-size="7.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Output</text>
            <text x="280" y="203" font-size="6.5" fill="#7b341e" text-anchor="middle">Verified?</text>

            <!-- Self-Healing Loop -->
            <path d="M 215 196 L 115 196 L 115 152 L 160 152" fill="none" stroke="#c0392b" stroke-width="1.3" marker-end="url(#arr-red10)"/>
            <text x="135" y="190" font-size="7" font-weight="bold" fill="#c0392b">No: Self-Heal</text>
            <text x="135" y="180" font-size="6" fill="#742a2a">(Recalibrate & Retry)</text>

            <line x1="280" y1="212" x2="280" y2="228" stroke="#27ae60" stroke-width="1.3" marker-end="url(#arr10)"/>
            <text x="286" y="222" font-size="7" font-weight="bold" fill="#27ae60">Yes</text>

            <rect x="180" y="228" width="200" height="22" rx="11" fill="#1a365d"/>
            <text x="280" y="242" font-size="8" font-weight="bold" fill="#ffffff" text-anchor="middle">Multi-Step Goal Achieved</text>
          </svg>
          <div class="fig-cap">Figure 5.2: Multi-agent swarm delegation and dynamic DAG execution pipeline</div>
        </div>

        <h2 class="sub-title">5.6 Native Windows OS Automation & MCP Protocol</h2>
        <p>
          <strong>Windows Actuation:</strong> Operates at the native Win32 layer using `pywin32`, `pywinauto`, and `pyautogui`. It dynamically 
          manages window focus, sends simulated keyboard strokes, adjusts hardware volume via `pycaw`, and launches software indexed from 
          the Windows Registry and Start Menu without hardcoded executable paths.
        </p>
        <p>
          <strong>Model Context Protocol (MCP):</strong> Implements the open MCP specification via JSON-RPC, connecting agents to 
          isolated tool servers including `filesystem` (safe directory operations), `github` (repository issue/PR tracking), and local databases.
        </p>

        <h2 class="sub-title">5.7 27 Continuous Learning Systems & Hinglish Adaptation</h2>
        <p>
          PULSAR integrates 27 algorithmic learning modules that evolve with the user without catastrophic neural forgetting:
        </p>
        <ul>
          <li><strong>Hinglish Code-Switching Drift:</strong> Actively maps bilingual Indian phrasing (e.g., <em>"bhai ye window band kar de"</em> &rarr; close active window) into formal OS actuation schemas.</li>
          <li><strong>Ebbinghaus Memory Decay:</strong> Continuously adjusts episodic memory retention weights, fading stale facts while reinforcing frequently accessed user preferences.</li>
          <li><strong>Reinforcement Learning from Human Feedback (RLHF):</strong> Records thumbs-up/down ratings to fine-tune tool parameter selection and conversational tone.</li>
          <li><strong>Hardware Adaptive Throttling:</strong> Telemetry monitors CPU and RAM load in real-time, throttling background tasks when the user launches demanding games or development suites.</li>
        </ul>
      </div>
      <div class="page-footer">Page 10</div>
    </div>
    """
    pages.append(p10)

    # =========================================================================
    # PAGE 11: 6. DATABASE DESIGN
    # =========================================================================
    p11 = """
    <div class="page" id="page-11">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">6. DATABASE DESIGN</h1>

        <h2 class="sub-title">6.1 Database Partitioning Architecture</h2>
        <p>
          PULSAR avoids monolithic database locking by partitioning persistent state across eight dedicated SQLite databases in `data/`. 
          Thread-safe connection pooling ensures background worker threads, audio listeners, and WebSocket handlers write concurrently 
          without contention. High-speed conversational context retrieval utilizes SQLite `FTS5` virtual tables, delivering sub-15ms 
          BM25 ranking with zero external vector database overhead.
        </p>

        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 20%;">Database</th>
              <th style="width: 25%;">Physical File</th>
              <th style="width: 55%;">Entity Purpose and Key Stored Attributes</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>App Usage</td>
              <td><code>app_usage.db</code></td>
              <td>Tracks application execution counts, focus durations, executable paths, and K-Means usage time clusters.</td>
            </tr>
            <tr>
              <td>Chat History</td>
              <td><code>chat_history.db</code></td>
              <td>Stores conversational message turns, role definitions, model metadata, token consumption, and timestamps.</td>
            </tr>
            <tr>
              <td>Conversation AI</td>
              <td><code>conversation_ai.db</code></td>
              <td>Maintains serialized multi-turn session states, active agent goals, and assistant personality parameters.</td>
            </tr>
            <tr>
              <td>Enhanced Learning</td>
              <td><code>enhanced_learning.db</code></td>
              <td>Stores active learning prompts, RLHF feedback rewards, intent drift training pairs, and accuracy benchmarks.</td>
            </tr>
            <tr>
              <td>Language Data</td>
              <td><code>language_data.db</code></td>
              <td>Maintains multilingual dictionary mappings, personalized colloquial phrases, and Hinglish vocabulary tokens.</td>
            </tr>
            <tr>
              <td>Memory Core</td>
              <td><code>memory.db</code></td>
              <td>Core long-term episodic knowledge repository utilizing SQLite FTS5 virtual tables, semantic triples, and decay scores.</td>
            </tr>
            <tr>
              <td>Personal Knowledge</td>
              <td><code>personal_knowledge.db</code></td>
              <td>Stores user-defined operational rules, custom macros, application shortcut profiles, and private encrypted notes.</td>
            </tr>
            <tr>
              <td>Chain History</td>
              <td><code>chain_history.db</code></td>
              <td>Logs multi-step autonomous execution traces, task DAG states, tool execution parameters, and self-healing retries.</td>
            </tr>
          </tbody>
        </table>

        <h2 class="sub-title">6.2 State Model & Episodic Memory Retention Pipeline</h2>
        <p>
          Autonomous tasks progress through a rigorous deterministic state machine: <code>PENDING</code> &rarr; <code>PARSING</code> &rarr; 
          <code>PLANNING</code> &rarr; <code>AWAITING_PIN</code> (if privileged) &rarr; <code>EXECUTING</code> &rarr; <code>VERIFYING</code> &rarr; 
          <code>COMPLETED</code>. Figure 6.1 outlines how user interactions are indexed, evaluated for decay, and retrieved for prompt injection.
        </p>

        <div class="fig-box">
          <svg width="550" height="150" viewBox="0 0 560 155" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <defs>
              <marker id="arr11" markerWidth="6" markerHeight="4" refX="5" refY="2" orient="auto">
                <polygon points="0 0, 6 2, 0 4" fill="#2c3e50" />
              </marker>
            </defs>

            <rect x="15" y="10" width="150" height="34" rx="5" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="90" y="24" font-size="7.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Interaction Stream</text>
            <text x="90" y="34" font-size="6.5" fill="#4a5568" text-anchor="middle">Voice, Chat & System Telemetry</text>

            <line x1="165" y1="27" x2="200" y2="27" stroke="#2c3e50" stroke-width="1.2" marker-end="url(#arr11)"/>

            <rect x="200" y="10" width="160" height="34" rx="5" fill="#f0fff4" stroke="#38a169" stroke-width="1.2"/>
            <text x="280" y="24" font-size="7.5" font-weight="bold" fill="#276749" text-anchor="middle">Triple & Entity Extractor</text>
            <text x="280" y="34" font-size="6.5" fill="#4a5568" text-anchor="middle">Subject-Predicate-Object Parsing</text>

            <line x1="360" y1="27" x2="395" y2="27" stroke="#2c3e50" stroke-width="1.2" marker-end="url(#arr11)"/>

            <rect x="395" y="10" width="150" height="34" rx="5" fill="#e6fffa" stroke="#319795" stroke-width="1.2"/>
            <text x="470" y="24" font-size="7.5" font-weight="bold" fill="#234e52" text-anchor="middle">SQLite FTS5 Storage</text>
            <text x="470" y="34" font-size="6.5" fill="#285e61" text-anchor="middle">BM25 Inverted Document Index</text>

            <path d="M 470 44 L 470 75 L 360 75" fill="none" stroke="#2c3e50" stroke-width="1.2" marker-end="url(#arr11)"/>

            <rect x="200" y="60" width="160" height="32" rx="5" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="280" y="73" font-size="7.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Ebbinghaus Memory Decay</text>
            <text x="280" y="83" font-size="6.5" fill="#7b341e" text-anchor="middle">Exponential Weight Recalibration</text>

            <path d="M 200 76 L 90 76 L 90 105" fill="none" stroke="#2c3e50" stroke-width="1.2" marker-end="url(#arr11)"/>

            <rect x="15" y="105" width="150" height="34" rx="5" fill="#faf5ff" stroke="#805ad5" stroke-width="1.2"/>
            <text x="90" y="119" font-size="7.5" font-weight="bold" fill="#6b46c1" text-anchor="middle">Context Query Pipeline</text>
            <text x="90" y="129" font-size="6.5" fill="#553c9a" text-anchor="middle">Hybrid BM25 + Recency Ranking</text>

            <line x1="165" y1="122" x2="200" y2="122" stroke="#2c3e50" stroke-width="1.2" marker-end="url(#arr11)"/>

            <rect x="200" y="105" width="345" height="34" rx="5" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="372" y="119" font-size="7.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Prompt Injection & Cognitive Synthesis</text>
            <text x="372" y="129" font-size="6.5" fill="#4a5568" text-anchor="middle">Relevant episodic facts injected into Gemini / Llama 3 context window</text>
          </svg>
          <div class="fig-cap">Figure 6.1: Long-term episodic memory extraction, decay scoring, and prompt synthesis pipeline</div>
        </div>
      </div>
      <div class="page-footer">Page 11</div>
    </div>
    """
    pages.append(p11)

    # =========================================================================
    # PAGE 12: 7. IMPLEMENTATION & 8. TESTING (PART 1)
    # =========================================================================
    p12 = """
    <div class="page" id="page-12">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">7. IMPLEMENTATION & 8. TESTING</h1>

        <h2 class="sub-title">7.1 Technical Implementation Stack</h2>
        <p>
          <strong>Frontend HUD:</strong> React 18, TypeScript, Vite, Tailwind CSS, Lucide icons, Recharts telemetry, and `@mediapipe/tasks-vision`. Implements an Iron Man JARVIS theme with pulsing Arc Reactor audio visualizers and floating spatial cursor.<br/>
          <strong>Backend Gateway:</strong> Python 3.10+ Flask 3.1 server structured into 11 domain blueprints with Flask-SocketIO WebSockets.<br/>
          <strong>Cognitive Engine:</strong> Cloud Google Gemini (Gemini 2.5 Flash / 2.0 Pro) paired with local fine-tuned Llama 3.1 8B Instruct (Q4_K_M GGUF, 4.92 GB) via `llama-cpp-python` with speculative decoding and prompt caching.<br/>
          <strong>OS Actuation & MCP:</strong> `pywin32`, `pywinauto`, `pyautogui`, `pycaw`, and Model Context Protocol (MCP) clients.<br/>
          <strong>Packaging & Deployment:</strong> Standalone desktop packaging via PyWebView and automated PowerShell launch scripts (`start.bat`).
        </p>

        <h2 class="sub-title">8.1 Testing Methodology & Empirical Verification</h2>
        <p>
          Testing was conducted across 42+ automated test suites in `tests/` using `pytest`. The system was validated across 
          cloud API latency, offline GGUF fallback, spatial hand tracking accuracy, Win32 window focus, and SQLite FTS5 query latency.
        </p>

        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 32%;">Test Case & Scope</th>
              <th style="width: 54%;">Expected Validation Metric</th>
              <th style="width: 14%; text-align: center;">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Gemini Cloud Token Streaming</td>
              <td>First token received in &lt;1.2s; streaming completes with zero socket dropouts.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Offline GGUF Fallback</td>
              <td>Seamlessly shifts to local Llama 3 8B model upon network loss within 200ms.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Real-Time Streaming Voice VAD</td>
              <td>Faster-Whisper in-memory transcription completes with latency under 250ms.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Contactless Spatial Cursor</td>
              <td>MediaPipe tracks hand gestures; pinch movement triggers accurate GUI click.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Gemini Vision Scene Analysis</td>
              <td>Accurately describes multi-window desktop screen layout and active error dialogs.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Privileged Action PIN Gate</td>
              <td>Intercepts file deletion and app termination; unlocks only on valid SHA-256 PIN.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Native Win32 Window Focus</td>
              <td>Brings target desktop software into foreground and simulates keystrokes.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>AutoGen Multi-Agent Swarm</td>
              <td>Decomposes compound research goal across Writer, Research, and Analyst agents.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Hinglish Intent Adaptation</td>
              <td>Correctly parses code-mixed colloquial Hindi-English input into formal actions.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>SQLite FTS5 BM25 Memory Recall</td>
              <td>Retrieves relevant historical conversation facts within 15ms.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Model Context Protocol (MCP)</td>
              <td>Executes filesystem search and file read via standard MCP JSON-RPC protocol.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Reactive Self-Healing Retry</td>
              <td>Recalculates click coordinates via OCR upon missed GUI button and succeeds.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="page-footer">Page 12</div>
    </div>
    """
    pages.append(p12)

    # =========================================================================
    # PAGE 13: 8. TESTING (PART 2) & 9. RESULTS, BENEFITS AND LIMITATIONS
    # =========================================================================
    p13 = """
    <div class="page" id="page-13">
      <div class="page-border"></div>
      <div>
        <h2 class="sub-title" style="margin-top: 0;">8.2 Self-Healing Diagnostics & Latency Analysis</h2>
        <p>
          PULSAR features an automated Self-Healing Engine: if an automation task fails due to a relocated desktop button or window, 
          the system captures an updated screen frame, runs Tesseract OCR and Gemini Vision to recalculate bounding coordinates, 
          and retries the operation up to three times. Unhandled exceptions are intercepted by centralized Flask middleware, logging 
          encrypted tracebacks while maintaining an active WebSocket session. Empirical testing verified sub-250ms voice transcription, 
          sub-10ms intent dispatch for cached actions, and sustained 12–18 tokens/sec on local GGUF fallback under 6.5 GB RAM.
        </p>

        <h1 class="sec-title" style="margin-top: 7pt;">9. RESULTS, BENEFITS AND LIMITATIONS</h1>

        <h2 class="sub-title">9.1 Results</h2>
        <p>
          The completed PULSAR system delivers a fully functional, hybrid AI operating assistant. The platform seamlessly integrates 
          Google Gemini 2.5 Flash cloud reasoning with a 4.92 GB fine-tuned local GGUF fallback, Faster-Whisper streaming speech transcription, 
          MediaPipe contactless hand-tracking, a 14-agent AutoGen swarm, Model Context Protocol tools, and native Windows PyWin32 automation.
        </p>

        <h2 class="sub-title">9.2 Distinctive System Benefits</h2>
        <ul>
          <li><strong>Hybrid Cloud-Edge Flexibility:</strong> Delivers elite foundation model reasoning via Google Gemini, while maintaining an offline GGUF fallback ensuring the user is never left without assistance.</li>
          <li><strong>Direct Operating System Actuation:</strong> Transcends passive chatbots by actively manipulating desktop windows, running applications, and automating multi-step chained workflows.</li>
          <li><strong>Contactless Spatial Interaction:</strong> Empowers users to interact with their PC via webcam hand-tracking gestures (pinch-to-click) alongside hands-free voice radar.</li>
          <li><strong>Autonomous Multi-Agent Swarm:</strong> Automates end-to-end research, document drafting, data analysis, and media controls through 14 collaborative domain agents.</li>
          <li><strong>Zero Telemetry Leakage for Local Actions:</strong> Local OS operations, file browsing, and sensitive commands execute entirely on-device behind a salted PIN security gate.</li>
          <li><strong>Personalized Memory Retention:</strong> Remembers user context and adapts to colloquial Hinglish slang across desktop reboots via zero-dependency SQLite FTS5 databases.</li>
        </ul>

        <h2 class="sub-title">9.3 Limitations & Academic Significance</h2>
        <p>
          <strong>Limitations:</strong> Full cloud features (broad web scraping, high-level code synthesis) require an active internet connection; local GGUF inference requires at least 8 GB of host RAM; and MediaPipe hand tracking requires adequate ambient room lighting.
        </p>
        <p>
          <strong>Academic Significance:</strong> Demonstrates the practical convergence of cloud foundation models, edge machine learning, low-level OS APIs, computer vision, digital signal processing, and multi-agent coordination in an engineered production software artifact.
        </p>
      </div>
      <div class="page-footer">Page 13</div>
    </div>
    """
    pages.append(p13)

    # =========================================================================
    # PAGE 14: 10. FUTURE SCOPE & CONCLUSION, 11. REFERENCES
    # =========================================================================
    p14 = """
    <div class="page" id="page-14">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">10. FUTURE SCOPE & CONCLUSION</h1>

        <h2 class="sub-title">10.1 Future Scope & Conclusion</h2>
        <p>
          <strong>Future Scope:</strong> Cross-platform automation support for Linux (X11/Wayland) and macOS (Accessibility APIs); on-device lightweight Vision-Language Model (VLM) for direct pixel-based navigation without OCR; peer-to-peer encrypted memory synchronization across mobile and desktop devices; and dynamic LoRA adapter hot-swapping for niche domains.
        </p>
        <p>
          <strong>Conclusion:</strong> PULSAR successfully resolves the trade-off between cloud intelligence and local execution. By fusing Google Gemini's cognitive prowess with native Windows automation, spatial gesture tracking, multi-agent swarms, and local offline resilience, PULSAR transforms the personal computer into a proactive, intelligent partner.
        </p>
        <p>
          <strong>Learning Outcomes:</strong> Hands-on mastery in hybrid AI architectures, quantized LLMs, C++ bindings, asynchronous Flask and WebSockets, modern React/TypeScript UI development, low-level Windows APIs, and multi-agent software engineering.
        </p>

        <h1 class="sec-title" style="margin-top: 5pt;">11. REFERENCES AND APPENDIX</h1>

        <h2 class="sub-title">11.1 References</h2>
        <ol style="margin-bottom: 3pt; font-size: 10pt;">
          <li>Google DeepMind, "Gemini: A Family of Highly Capable Multimodal Models," Technical Report, 2024.</li>
          <li>Meta AI, "Llama 3 Herd of Models: Architecture, Quantization, and Capabilities," Technical Report, 2024.</li>
          <li>Gerganov, G., "llama.cpp: Efficient Port of LLaMA Architecture in C/C++," GitHub Repository, 2024.</li>
          <li>Radford, A. et al., "Robust Speech Recognition via Large-Scale Weak Supervision," OpenAI Whisper, 2023.</li>
          <li>Lugaresi, C. et al., "MediaPipe: A Framework for Building Perception Pipelines," Google Research, 2019.</li>
          <li>Wu, Q. et al., "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation," Microsoft Research, 2023.</li>
          <li>Anthropic, "Model Context Protocol (MCP) Specification," Open-Source Standard, 2024.</li>
          <li>SQLite Consortium, "SQLite FTS5 Extension: Full-Text Search and BM25 Ranking," 2024.</li>
          <li>Hammond, M., "Python for Windows Extensions (pywin32): Accessing Native Subsystems," 2023.</li>
          <li>OWASP Foundation, "Top 10 Considerations for Agentic AI Applications," 2024.</li>
        </ol>

        <h2 class="sub-title">11.2 Core System Endpoints & Technology Stack Summary</h2>
        <table class="data-table" style="font-size: 9pt; margin-top: 2pt;">
          <thead>
            <tr>
              <th style="width: 25%;">Layer / Subsystem</th>
              <th style="width: 75%;">Integrated Technologies and Core Routes</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Frontend Client HUD</td>
              <td>React 18, Vite, TypeScript, Tailwind CSS, Lucide, Recharts, PyWebView native wrapper</td>
            </tr>
            <tr>
              <td>API Gateway & Blueprints</td>
              <td>Flask 3.1, Flask-SocketIO; <code>/api/auth/*</code>, <code>/api/chat/*</code>, <code>/api/system/*</code>, <code>/api/apps/*</code></td>
            </tr>
            <tr>
              <td>Hybrid Cognitive Brain</td>
              <td>Google Gemini 2.5 Flash / 2.0 Pro (Cloud) + Llama 3 8B Q4 GGUF (4.92 GB on AVX2 CPU)</td>
            </tr>
            <tr>
              <td>Perception & Spatial UI</td>
              <td>Faster-Whisper STT, Edge Neural TTS, KittenTTS, MediaPipe Hands, Gemini Vision, Tesseract 5</td>
            </tr>
            <tr>
              <td>Multi-Agent Swarm & MCP</td>
              <td>14 AutoGen Agents (loader.py, dispatcher.py), Model Context Protocol (mcp_client.py)</td>
            </tr>
            <tr>
              <td>OS Actuation & Persistence</td>
              <td>PyWin32, PyAutoGUI, PyCAW, Registry API; 8 SQLite DBs with FTS5 virtual tables</td>
            </tr>
          </tbody>
        </table>

        <div style="text-align: center; margin-top: 5pt; font-size: 9.5pt; font-weight: bold; letter-spacing: 0.5px;">
          End of Synopsis &mdash; <span style="font-size: 10.5pt; letter-spacing: 1.5px;">PULSAR</span>
        </div>
      </div>
      <div class="page-footer">Page 14</div>
    </div>
    """
    pages.append(p14)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>PULSAR - Major Project Synopsis</title>
  <style>
{css}
  </style>
</head>
<body>
{''.join(pages)}
</body>
</html>
"""
    return html_content

def build_markdown():
    md = """# “PULSAR”
## An Autonomous Hybrid Cloud-Edge Agentic AI Platform with Multimodal Vision, Spatial Gesture Interaction, and Native Windows Automation

**SYNOPSIS OF MAJOR PROJECT**  
of  
**Bachelor of Technology**  
in  
**Computer Science & Engineering**  

### Group Details
| S.No. | Student Name | Roll Number | Branch and Section |
| :---: | :--- | :---: | :---: |
| 1 | **Diwakar Chaurasia (Group Leader)** | 23016501000073 | Computer Science & Engineering |
| 2 | **Raghav Bajpai** | 230165010000119 | Computer Science & Engineering |
| 3 | **Ghanshyam Jha** | 23016501000076 | Computer Science & Engineering |
| 4 | **Abhishek Sharma** | 23016501000010 | Computer Science & Engineering |

**Kanpur Institute of Technology, Kanpur**  
**Dr. A.P.J. Abdul Kalam Technical University, Lucknow**  
**Academic Session: 2026–27**  

---

## DECLARATION
We hereby declare that this submission is our own work and that, to the best of our knowledge and belief, it contains no material previously published or written by another person nor material which to a substantial extent has been accepted for the award of any other degree or diploma by the university or other institute of higher learning, except where due acknowledgement has been made in the text.

### Signatures:
1. **Diwakar Chaurasia (Leader)** — Roll No: 23016501000073  
2. **Raghav Bajpai** — Roll No: 230165010000119  
3. **Ghanshyam Jha** — Roll No: 23016501000076  
4. **Abhishek Sharma** — Roll No: 23016501000010  

Date: ________________________  

**Approved By:**  
**Rahul Singh**  
Head of Department, Computer Science and Engineering  
KIT, KANPUR  
Signature: _________________________________________  

---

## TABLE OF CONTENTS
| No. | Particulars | Page |
| :---: | :--- | :---: |
| 1. | Introduction | 4 |
| 2. | Objectives and System Study | 5 |
| 3. | Requirement Analysis | 7 |
| 4. | System Architecture and Design | 8 |
| 5. | Module Description | 9 |
| 6. | Database Design | 11 |
| 7. | Implementation | 12 |
| 8. | Testing and Validation | 12 |
| 9. | Results, Benefits and Limitations | 13 |
| 10. | Future Scope and Conclusion | 14 |
| 11. | References and Appendix | 14 |

---

*(Full technical content matching the 14-page format is available in the compiled PDF and HTML files).*
"""
    return md

def compile_pdf():
    print(f"Compiling PDF via Microsoft Edge: {PDF_PATH}")
    cmd = [
        EDGE_PATH,
        "--headless",
        "--disable-gpu",
        "--print-to-pdf-no-header",
        "--no-margins",
        f"--print-to-pdf={PDF_PATH}",
        f"file:///{HTML_PATH.replace(os.sep, '/')}"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(PDF_PATH):
        with open(PDF_PATH, "rb") as f:
            pdf_data = f.read()
        page_count = len(re.findall(rb'/Type\s*/Page\b', pdf_data))
        file_size_kb = len(pdf_data) / 1024
        print(f"PDF successfully generated!")
        print(f"Total Pages: {page_count}")
        print(f"File Size: {file_size_kb:.2f} KB")

        # Copy to Desktop
        try:
            with open(DESKTOP_PDF_PATH, "wb") as f_out:
                f_out.write(pdf_data)
            print(f"Copied updated PDF to Desktop: {DESKTOP_PDF_PATH}")
        except Exception as e:
            print(f"Failed to copy to Desktop: {e}")

        return page_count
    else:
        print("PDF generation failed.")
        return 0

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generating HTML...")
    html = build_html()
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved HTML to: {HTML_PATH}")

    print("Generating Markdown documentation...")
    md = build_markdown()
    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Saved Markdown to: {MD_PATH}")

    print("Compiling PDF...")
    pages = compile_pdf()
    print(f"Process complete. Generated {pages} pages.")

if __name__ == "__main__":
    main()
