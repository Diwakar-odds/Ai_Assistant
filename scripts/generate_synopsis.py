"""
PULSAR Major Project Synopsis Generator
Generates a complete 20-page academic synopsis document for B.Tech Computer Science & Engineering
matching the formatting, structure, tables, and vector SVG diagrams of the AKTU / Kanpur Institute of Technology standard.
"""

import os
import subprocess
import re

OUTPUT_DIR = r"d:\Projects\Ai_Assistant\docs"
HTML_PATH = os.path.join(OUTPUT_DIR, "PULSAR_Major_Project_Synopsis.html")
PDF_PATH = os.path.join(OUTPUT_DIR, "PULSAR_Major_Project_Synopsis.pdf")
MD_PATH = os.path.join(OUTPUT_DIR, "PULSAR_Major_Project_Synopsis.md")
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def build_html():
    # Common styles
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
      font-family: 'Times New Roman', Times, Georgia, serif;
      color: #111;
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
      padding: 16mm 20mm;
      position: relative;
      background: #ffffff;
      page-break-after: always;
      break-after: page;
      overflow: hidden;
    }
    .page-border {
      position: absolute;
      top: 10mm;
      left: 12mm;
      right: 12mm;
      bottom: 10mm;
      border: 1.5px solid #111111;
      pointer-events: none;
    }
    .page-footer {
      position: absolute;
      bottom: 12.5mm;
      left: 0;
      right: 0;
      text-align: center;
      font-size: 10pt;
      font-family: 'Times New Roman', Times, serif;
    }
    h1.sec-title {
      font-size: 13.5pt;
      font-weight: bold;
      text-align: center;
      margin-top: 0;
      margin-bottom: 11pt;
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }
    h2.sub-title {
      font-size: 11pt;
      font-weight: bold;
      margin-top: 8pt;
      margin-bottom: 3.5pt;
    }
    p {
      font-size: 10pt;
      line-height: 1.34;
      margin: 4.5pt 0;
      text-align: justify;
    }
    ul {
      margin: 3.5pt 0;
      padding-left: 18pt;
    }
    li {
      font-size: 10pt;
      line-height: 1.32;
      margin-bottom: 3pt;
      text-align: justify;
    }
    ol {
      margin: 3.5pt 0;
      padding-left: 18pt;
    }
    ol li {
      font-size: 10pt;
      line-height: 1.32;
      margin-bottom: 2.8pt;
      text-align: justify;
    }
    table.data-table {
      width: 100%;
      border-collapse: collapse;
      margin: 6.5pt 0;
      font-size: 9.3pt;
    }
    table.data-table th, table.data-table td {
      border: 1px solid #222;
      padding: 4.2pt 5.5pt;
      vertical-align: top;
      line-height: 1.25;
    }
    table.data-table th {
      font-weight: bold;
      background-color: #fafafa;
    }
    .fig-box {
      text-align: center;
      margin: 6pt 0;
    }
    .fig-cap {
      font-size: 9.5pt;
      font-weight: bold;
      text-align: center;
      margin-top: 5pt;
      margin-bottom: 3pt;
    }
    """

    pages = []

    # =========================================================================
    # PAGE 1: TITLE PAGE
    # =========================================================================
    p1 = """
    <div class="page" id="page-1">
      <div class="page-border"></div>
      <div style="text-align: center; padding-top: 18mm;">
        <div style="font-size: 26pt; font-weight: bold; letter-spacing: 1.5px; margin-bottom: 12pt;">“PULSAR”</div>
        <div style="font-size: 13.5pt; font-weight: bold; line-height: 1.45; max-width: 155mm; margin: 0 auto 32pt auto;">
          A Native OS Automation and Multi-Modal Agentic AI Assistant for Windows
        </div>
        
        <div style="font-size: 13.5pt; font-weight: bold; letter-spacing: 0.5px; margin-bottom: 6pt;">SYNOPSIS OF MAJOR PROJECT</div>
        <div style="font-size: 11pt; margin-bottom: 4pt;">of</div>
        <div style="font-size: 13pt; font-weight: bold; margin-bottom: 4pt;">Bachelor of Technology</div>
        <div style="font-size: 11pt; margin-bottom: 4pt;">in</div>
        <div style="font-size: 13pt; font-weight: bold; margin-bottom: 8pt;">Computer Science & Engineering</div>
        <div style="font-size: 11.5pt; margin-bottom: 12pt;">By</div>

        <table style="width: 95%; margin: 0 auto 35pt auto; border-collapse: collapse; font-size: 10pt;">
          <thead>
            <tr style="background: #fafafa;">
              <th style="border: 1px solid #222; padding: 6pt 10pt; font-weight: bold; width: 8%;">S.No.</th>
              <th style="border: 1px solid #222; padding: 6pt 12pt; font-weight: bold; width: 34%;">Student Name</th>
              <th style="border: 1px solid #222; padding: 6pt 12pt; font-weight: bold; width: 28%;">Roll Number</th>
              <th style="border: 1px solid #222; padding: 6pt 12pt; font-weight: bold; width: 30%;">Branch and Section</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="border: 1px solid #222; padding: 6pt 10pt; text-align: center;">1</td>
              <td style="border: 1px solid #222; padding: 6pt 12pt; text-align: center; font-weight: 500;">Diwakar Singh</td>
              <td style="border: 1px solid #222; padding: 6pt 12pt; text-align: center;">2301650100004</td>
              <td style="border: 1px solid #222; padding: 6pt 12pt; text-align: center;">Computer Science & Engineering</td>
            </tr>
          </tbody>
        </table>

        <!-- KIT Logo / Emblem -->
        <div style="margin: 0 auto 14pt auto; width: 140px; text-align: center;">
          <svg width="130" height="42" viewBox="0 0 200 65" xmlns="http://www.w3.org/2000/svg">
            <path d="M15 45 L35 15 L55 45 L42 45 L35 32 L28 45 Z" fill="#999999" opacity="0.6"/>
            <path d="M30 48 L48 20 L66 48 L54 48 L48 37 L42 48 Z" fill="#1b499c" opacity="0.4"/>
            <text x="75" y="48" font-family="'Arial Black', Arial, sans-serif" font-size="44" font-weight="900" fill="#143975" letter-spacing="1">KIT</text>
            <circle cx="152" cy="18" r="6" fill="#44aa44"/>
            <path d="M152 10 L152 26 M144 18 L160 18 M146 12 L158 24 M146 24 L158 12" stroke="#ffffff" stroke-width="2"/>
            <text x="144" y="30" font-family="Arial, sans-serif" font-size="9" font-weight="bold" fill="#555555">Estd. 2004</text>
          </svg>
        </div>

        <div style="font-size: 12.5pt; font-weight: bold; margin-bottom: 4pt;">Kanpur Institute of Technology, Kanpur</div>
        <div style="font-size: 11.5pt; font-weight: bold; margin-bottom: 5pt;">Dr. A.P.J. Abdul Kalam Technical University, Lucknow</div>
        <div style="font-size: 11pt; font-weight: bold;">Academic Session: 2026–27</div>
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
      <div style="padding-top: 16mm;">
        <div style="font-size: 14pt; font-weight: bold; text-align: center; margin-bottom: 24pt; letter-spacing: 0.5px;">DECLARATION</div>
        
        <p style="font-size: 10.5pt; line-height: 1.55; text-align: justify; margin-bottom: 35pt;">
          We hereby declare that this submission is our own work and that, to the best of our knowledge and 
          belief, it contains no material previously published or written by another person nor material which to 
          a substantial extent has been accepted for the award of any other degree or diploma by the university 
          or other institute of higher learning, except where due acknowledgement has been made in the text.
        </p>

        <div style="margin-bottom: 55pt; font-size: 10.5pt; line-height: 1.6;">
          <div>Signature: _________________________________________</div>
          <br/>
          <div>Name: Diwakar Singh</div>
          <div>Roll No: 2301650100004</div>
          <div>Date: ________________________</div>
        </div>

        <div style="margin-top: 75pt; font-size: 10.5pt; line-height: 1.5;">
          <div style="font-weight: bold; margin-bottom: 12pt;">Approved By:</div>
          <br/><br/>
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
      <div style="padding-top: 14mm;">
        <div style="font-size: 14pt; font-weight: bold; text-align: center; margin-bottom: 18pt; letter-spacing: 0.5px;">TABLE OF CONTENTS</div>
        
        <table style="width: 100%; border-collapse: collapse; font-size: 10.5pt; margin-top: 8pt;">
          <thead>
            <tr style="background: #fafafa;">
              <th style="border: 1px solid #222; padding: 7pt 10pt; width: 12%; text-align: left; font-weight: bold;">No.</th>
              <th style="border: 1px solid #222; padding: 7pt 12pt; width: 70%; text-align: left; font-weight: bold;">Particulars</th>
              <th style="border: 1px solid #222; padding: 7pt 10pt; width: 18%; text-align: center; font-weight: bold;">Page</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt;">1.</td>
              <td style="border: 1px solid #222; padding: 6.5pt 12pt;">Introduction</td>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt; text-align: center;">4</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt;">2.</td>
              <td style="border: 1px solid #222; padding: 6.5pt 12pt;">Objectives and System Study</td>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt; text-align: center;">5</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt;">3.</td>
              <td style="border: 1px solid #222; padding: 6.5pt 12pt;">Requirement Analysis</td>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt; text-align: center;">7</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt;">4.</td>
              <td style="border: 1px solid #222; padding: 6.5pt 12pt;">System Architecture and Design</td>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt; text-align: center;">8</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt;">5.</td>
              <td style="border: 1px solid #222; padding: 6.5pt 12pt;">Module Description</td>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt; text-align: center;">10</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt;">6.</td>
              <td style="border: 1px solid #222; padding: 6.5pt 12pt;">Database Design</td>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt; text-align: center;">13</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt;">7.</td>
              <td style="border: 1px solid #222; padding: 6.5pt 12pt;">Implementation</td>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt; text-align: center;">15</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt;">8.</td>
              <td style="border: 1px solid #222; padding: 6.5pt 12pt;">Testing and Validation</td>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt; text-align: center;">16</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt;">9.</td>
              <td style="border: 1px solid #222; padding: 6.5pt 12pt;">Results, Benefits and Limitations</td>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt; text-align: center;">18</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt;">10.</td>
              <td style="border: 1px solid #222; padding: 6.5pt 12pt;">Future Scope and Conclusion</td>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt; text-align: center;">19</td>
            </tr>
            <tr>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt;">11.</td>
              <td style="border: 1px solid #222; padding: 6.5pt 12pt;">References and Appendix</td>
              <td style="border: 1px solid #222; padding: 6.5pt 10pt; text-align: center;">20</td>
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
          Personal computing workflows have expanded dramatically in scope and complexity. Modern users 
          routinely operate across dozens of simultaneous desktop windows, disparate software utilities, web 
          browsers, code editors, and file repositories. While modern Large Language Models (LLMs) have 
          demonstrated remarkable conversational and cognitive capabilities, the overwhelming majority of existing 
          AI assistants remain constrained within remote web browsers and sandboxed cloud environments. They act 
          as passive conversational advisors rather than active operating system actuating agents.
        </p>
        <p>
          PULSAR was developed as a unified, offline, multi-modal operating system automation platform for Windows. 
          It connects natural language and voice interaction directly to the underlying operating system environment, 
          allowing users to automate desktop applications, organize files, inspect system processes, perform real-time 
          screen OCR, and retrieve long-term context entirely on-device without exposing sensitive data to cloud servers.
        </p>

        <h2 class="sub-title">1.2 Problem Statement</h2>
        <p>
          Traditional commercial AI assistants (such as cloud-hosted chatbots and proprietary web extensions) suffer from 
          three fundamental architectural shortcomings:
        </p>
        <p>
          Firstly, they pose grave security and privacy risks because private system state, typed documents, and 
          personal queries must be transmitted over the public internet to third-party data centers. Secondly, they 
          lack native access to the operating system; they cannot click desktop buttons, switch active windows, 
          launch installed software, or manage local directory hierarchies. Thirdly, they impose recurring subscription 
          fees and high network latency that degrades hands-free voice usability.
        </p>
        <p>
          PULSAR addresses these challenges by implementing an air-gapped, zero-leakage desktop assistant architecture. 
          It leverages 4-bit quantized local GGUF models on consumer CPUs, integrates high-speed speech-to-text, 
          and uses native Windows Win32 APIs for safe, deterministic automation.
        </p>

        <h2 class="sub-title">1.3 Need for the System</h2>
        <ul>
          <li>100% offline edge execution ensuring absolute privacy, data ownership, and zero telemetry leakage.</li>
          <li>Direct Windows OS automation (GUI navigation, window management, keystrokes, and registry inspection).</li>
          <li>Real-time multimodal sensory perception combining fast streaming voice STT, TTS, and desktop OCR.</li>
          <li>Deterministic multi-agent task planning to break down complex goals into safe, verifiable execution steps.</li>
          <li>Continuous personalization using 27 programmatic learning paradigms that adapt to user habits and slang.</li>
          <li>Zero-dependency persistent memory utilizing SQLite FTS5 full-text search with zero cloud footprint.</li>
        </ul>

        <h2 class="sub-title">1.4 Scope of the Project</h2>
        <p>
          The scope includes a dual-engine architecture featuring a React + Vite + TypeScript desktop interface, a 
          modular Flask API gateway with 11 domain blueprints, local Q4_K_M GGUF Llama 3.1 8B CPU inference, 
          real-time speech recognition via faster-whisper, desktop vision and Tesseract OCR, PyWin32 automation 
          drivers, SQLite database clusters, PIN-based cryptographic security, and automated system diagnostics. 
          All modules are fully implemented in the working system.
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
          <li>Develop a high-performance offline AI desktop agent natively integrated into the Windows OS environment.</li>
          <li>Implement local quantized LLM inference (Llama 3.1 8B Q4_K_M GGUF) operating efficiently on consumer CPUs.</li>
          <li>Construct a multi-agent orchestration dispatcher for natural language goal decomposition and negotiation.</li>
          <li>Integrate real-time streaming speech recognition (faster-whisper) with acoustic emotion tracking and TTS.</li>
          <li>Provide visual desktop perception through window boundary tracking, screen capture, and Tesseract OCR.</li>
          <li>Build an OS automation engine using PyWin32 and PyAutoGUI for hands-free software navigation and control.</li>
          <li>Implement 27 continuous learning paradigms to dynamically adapt to user vocabulary, Hinglish slang, and habits.</li>
          <li>Provide zero-dependency long-term memory retrieval using SQLite FTS5 BM25 search and semantic graphs.</li>
          <li>Enforce strict PIN-based cryptographic authorization for privileged system, filesystem, and process controls.</li>
          <li>Package the complete system into a responsive native Windows desktop application using PyWebView.</li>
        </ol>

        <h2 class="sub-title">2.2 Existing System</h2>
        <p>
          Current AI assistant implementations fall into distinct, disconnected categories: cloud-based conversational 
          chatbots, browser-sandboxed extensions, and rigid desktop automation macros. None of these provide an integrated, 
          private, and autonomous desktop experience.
        </p>

        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 20%;">Area</th>
              <th style="width: 38%;">Typical Approach</th>
              <th style="width: 42%;">Limitation</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>OS Control</td>
              <td>Web-based chatbots (ChatGPT, Claude)</td>
              <td>Sandboxed inside browser; cannot interact with native apps or files.</td>
            </tr>
            <tr>
              <td>Data Privacy</td>
              <td>Cloud LLM REST APIs</td>
              <td>User prompts, files, and system data are sent to remote corporate servers.</td>
            </tr>
            <tr>
              <td>Latency & Cost</td>
              <td>Pay-per-token cloud subscriptions</td>
              <td>High network latency hampers voice interaction; ongoing monthly fees.</td>
            </tr>
            <tr>
              <td>Context & Memory</td>
              <td>Ephemeral session histories</td>
              <td>Loss of context across desktop reboots; expensive context window scaling.</td>
            </tr>
            <tr>
              <td>Desktop Macros</td>
              <td>Rigid RPA / AutoHotkey scripts</td>
              <td>Fragile to UI layout changes; incapable of cognitive reasoning or error recovery.</td>
            </tr>
          </tbody>
        </table>

        <h2 class="sub-title">2.3 Proposed System</h2>
        <p>
          PULSAR bridges the gap between neural cognitive reasoning and deterministic OS execution. The system runs 
          an edge-quantized cognitive engine coupled with a multi-agent dispatcher, perception pipelines, and native 
          Windows automation drivers. Complex user requests are autonomously decomposed into sequential sub-tasks, 
          validated through security checks, executed directly against native Windows applications, and remembered 
          across sessions via local SQLite databases.
        </p>
      </div>
      <div class="page-footer">Page 5</div>
    </div>
    """
    pages.append(p5)

    # =========================================================================
    # PAGE 6: FIGURE 2.1 (WORKFLOW DIAGRAM)
    # =========================================================================
    p6 = """
    <div class="page" id="page-6">
      <div class="page-border"></div>
      <div>
        <p style="font-size: 10pt; line-height: 1.35; margin-bottom: 8pt;">
          Figure 2.1 illustrates the overall user–agent interaction and autonomous execution workflow supported by 
          PULSAR, from multimodal sensory ingestion to deterministic OS actuation, self-healing verification, and persistent memory.
        </p>

        <div class="fig-box">
          <svg width="600" height="740" viewBox="0 0 600 740" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <defs>
              <marker id="arr" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#2c3e50" />
              </marker>
              <marker id="arr-green" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#27ae60" />
              </marker>
              <marker id="arr-red" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#c0392b" />
              </marker>
            </defs>

            <!-- GROUP: USER INTERACTION -->
            <rect x="30" y="15" width="230" height="340" rx="10" fill="#f0f7ff" stroke="#3182ce" stroke-width="1.2" stroke-dasharray="4,3"/>
            <text x="45" y="35" font-size="11" font-weight="bold" fill="#2b6cb0" letter-spacing="0.5">USER & CLIENT INTERACTION</text>

            <!-- Start Node -->
            <rect x="95" y="55" width="100" height="30" rx="15" fill="#2d3748" stroke="#1a202c"/>
            <text x="145" y="74" font-size="11" font-weight="bold" fill="#ffffff" text-anchor="middle">Start Command</text>
            
            <line x1="145" y1="85" x2="145" y2="105" stroke="#2c3e50" stroke-width="1.5" marker-end="url(#arr)"/>

            <!-- Modality Input Node -->
            <rect x="55" y="105" width="180" height="42" rx="6" fill="#ffffff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="145" y="122" font-size="10" font-weight="bold" fill="#2d3748" text-anchor="middle">Multimodal Input</text>
            <text x="145" y="137" font-size="8.5" fill="#4a5568" text-anchor="middle">(Voice Stream / Text / Hotkey)</text>

            <line x1="145" y1="147" x2="145" y2="167" stroke="#2c3e50" stroke-width="1.5" marker-end="url(#arr)"/>

            <!-- Streaming STT / Perception Node -->
            <rect x="55" y="167" width="180" height="42" rx="6" fill="#e6fffa" stroke="#319795" stroke-width="1.2"/>
            <text x="145" y="184" font-size="10" font-weight="bold" fill="#234e52" text-anchor="middle">faster-whisper & OCR</text>
            <text x="145" y="199" font-size="8.5" fill="#285e61" text-anchor="middle">Acoustic & Vision Preprocessing</text>

            <line x1="145" y1="209" x2="145" y2="230" stroke="#2c3e50" stroke-width="1.5" marker-end="url(#arr)"/>

            <!-- Cognitive Intent Classification -->
            <rect x="55" y="230" width="180" height="44" rx="6" fill="#ffffff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="145" y="247" font-size="10" font-weight="bold" fill="#2d3748" text-anchor="middle">Intent Classifier &</text>
            <text x="145" y="262" font-size="9" fill="#4a5568" text-anchor="middle">Central Agent Dispatcher</text>

            <!-- GROUP: CORE AI & MULTI-AGENT ENGINE -->
            <rect x="330" y="15" width="240" height="340" rx="10" fill="#f0fff4" stroke="#38a169" stroke-width="1.2" stroke-dasharray="4,3"/>
            <text x="345" y="35" font-size="11" font-weight="bold" fill="#276749" letter-spacing="0.5">COGNITIVE ORCHESTRATION</text>

            <!-- Connector to Security Check -->
            <path d="M 235 252 L 285 252 L 285 70 L 370 70" fill="none" stroke="#2c3e50" stroke-width="1.5" marker-end="url(#arr)"/>

            <!-- Security PIN Decision Diamond -->
            <polygon points="450,50 515,75 450,100 385,75" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="450" y="73" font-size="9" font-weight="bold" fill="#7b341e" text-anchor="middle">Privileged</text>
            <text x="450" y="84" font-size="8.5" fill="#7b341e" text-anchor="middle">Command?</text>

            <!-- Branch: Yes -> PIN Check -->
            <line x1="515" y1="75" x2="540" y2="75" stroke="#dd6b20" stroke-width="1.5"/>
            <path d="M 540 75 L 540 125 L 450 125" fill="none" stroke="#dd6b20" stroke-width="1.5" marker-end="url(#arr)"/>
            <text x="532" y="68" font-size="8.5" font-weight="bold" fill="#c05621">Yes</text>

            <!-- PIN Node -->
            <rect x="375" y="112" width="150" height="28" rx="5" fill="#feebc8" stroke="#c05621" stroke-width="1.1"/>
            <text x="450" y="130" font-size="9" font-weight="bold" fill="#7b341e" text-anchor="middle">Verify PIN_HASH</text>

            <!-- Branch: No -> Direct Execution -->
            <line x1="450" y1="100" x2="450" y2="155" stroke="#2c3e50" stroke-width="1.5" marker-end="url(#arr)"/>
            <text x="455" y="108" font-size="8.5" font-weight="bold" fill="#27ae60">No</text>
            <line x1="450" y1="140" x2="450" y2="155" stroke="#2c3e50" stroke-width="1.5"/>

            <!-- Multi-Agent Task Decomposition -->
            <rect x="360" y="155" width="180" height="42" rx="6" fill="#ffffff" stroke="#38a169" stroke-width="1.2"/>
            <text x="450" y="172" font-size="10" font-weight="bold" fill="#2d3748" text-anchor="middle">Task Decomposition</text>
            <text x="450" y="187" font-size="8.5" fill="#4a5568" text-anchor="middle">Llama 3.1 8B GGUF Model</text>

            <line x1="450" y1="197" x2="450" y2="218" stroke="#2c3e50" stroke-width="1.5" marker-end="url(#arr)"/>

            <!-- Sub-Agents Registry -->
            <rect x="360" y="218" width="180" height="52" rx="6" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="450" y="234" font-size="9.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Sub-Agent Allocation</text>
            <text x="450" y="248" font-size="8" fill="#4a5568" text-anchor="middle">Productivity | Files | System</text>
            <text x="450" y="260" font-size="8" fill="#4a5568" text-anchor="middle">Audio | Research | Student</text>

            <line x1="450" y1="270" x2="450" y2="295" stroke="#2c3e50" stroke-width="1.5" marker-end="url(#arr)"/>

            <!-- Execution Step DAG -->
            <rect x="360" y="295" width="180" height="38" rx="6" fill="#ffffff" stroke="#38a169" stroke-width="1.2"/>
            <text x="450" y="312" font-size="9.5" font-weight="bold" fill="#2d3748" text-anchor="middle">Sequential Tool DAG</text>
            <text x="450" y="324" font-size="8" fill="#4a5568" text-anchor="middle">Deterministic Parameter Mapping</text>

            <!-- GROUP: OS ACTUATION & VERIFICATION -->
            <rect x="30" y="380" width="540" height="310" rx="10" fill="#faf5ff" stroke="#805ad5" stroke-width="1.2" stroke-dasharray="4,3"/>
            <text x="45" y="400" font-size="11" font-weight="bold" fill="#6b46c1" letter-spacing="0.5">NATIVE OS ACTUATION & CONTINUOUS LEARNING</text>

            <!-- Connector from DAG to Actuator -->
            <path d="M 450 333 L 450 360 L 300 360 L 300 420" fill="none" stroke="#2c3e50" stroke-width="1.5" marker-end="url(#arr)"/>

            <!-- OS Actuator Node -->
            <rect x="195" y="420" width="210" height="45" rx="6" fill="#ffffff" stroke="#805ad5" stroke-width="1.3"/>
            <text x="300" y="438" font-size="10" font-weight="bold" fill="#2d3748" text-anchor="middle">Windows Automation Engine</text>
            <text x="300" y="452" font-size="8.5" fill="#553c9a" text-anchor="middle">PyWin32 | PyAutoGUI | Registry API</text>

            <line x1="300" y1="465" x2="300" y2="488" stroke="#2c3e50" stroke-width="1.5" marker-end="url(#arr)"/>

            <!-- Verification Decision Diamond -->
            <polygon points="300,488 380,515 300,542 220,515" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="300" y="512" font-size="9.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Execution</text>
            <text x="300" y="523" font-size="8.5" fill="#7b341e" text-anchor="middle">Verified?</text>

            <!-- Branch: No -> Self-Healing Loop -->
            <path d="M 220 515 L 120 515 L 120 442 L 195 442" fill="none" stroke="#c0392b" stroke-width="1.5" marker-end="url(#arr-red)"/>
            <text x="145" y="508" font-size="8.5" font-weight="bold" fill="#c0392b">No: Self-Heal</text>
            <text x="145" y="495" font-size="7.5" fill="#742a2a">(OCR Traceback Retry)</text>

            <!-- Branch: Yes -> Memory & Telemetry -->
            <line x1="300" y1="542" x2="300" y2="568" stroke="#27ae60" stroke-width="1.5" marker-end="url(#arr-green)"/>
            <text x="308" y="555" font-size="8.5" font-weight="bold" fill="#27ae60">Yes</text>

            <!-- Memory & 27 Learning Engines -->
            <rect x="70" y="568" width="210" height="48" rx="6" fill="#e6fffa" stroke="#319795" stroke-width="1.2"/>
            <text x="175" y="585" font-size="9.5" font-weight="bold" fill="#234e52" text-anchor="middle">SQLite FTS5 & Learning Core</text>
            <text x="175" y="598" font-size="8" fill="#285e61" text-anchor="middle">27 Paradigms: Active Learning,</text>
            <text x="175" y="609" font-size="8" fill="#285e61" text-anchor="middle">Hinglish Drift, Ebbinghaus Decay</text>

            <!-- Feedback & UI Response -->
            <rect x="320" y="568" width="210" height="48" rx="6" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="425" y="585" font-size="9.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Multimodal Client Response</text>
            <text x="425" y="598" font-size="8" fill="#4a5568" text-anchor="middle">Pyttsx3/eSpeak-ng Voice TTS +</text>
            <text x="425" y="609" font-size="8" fill="#4a5568" text-anchor="middle">React Dashboard Telemetry Update</text>

            <line x1="175" y1="616" x2="175" y2="640" stroke="#2c3e50" stroke-width="1.5"/>
            <line x1="425" y1="616" x2="425" y2="640" stroke="#2c3e50" stroke-width="1.5"/>
            <line x1="175" y1="640" x2="425" y2="640" stroke="#2c3e50" stroke-width="1.5"/>
            <line x1="300" y1="640" x2="300" y2="658" stroke="#2c3e50" stroke-width="1.5" marker-end="url(#arr)"/>

            <!-- End Node -->
            <rect x="250" y="658" width="100" height="28" rx="14" fill="#2d3748" stroke="#1a202c"/>
            <text x="300" y="676" font-size="10.5" font-weight="bold" fill="#ffffff" text-anchor="middle">End State</text>
          </svg>
          <div class="fig-cap">Figure 2.1: Overall user–agent interaction and autonomous execution workflow of PULSAR</div>
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
          <li><strong>Natural Language & Voice Processing:</strong> Ingest real-time microphone streams, transcribe audio using faster-whisper, and parse natural text intents.</li>
          <li><strong>Edge LLM Inference:</strong> Execute 4-bit quantized GGUF models on CPU without requiring external APIs, cloud compute, or active internet connections.</li>
          <li><strong>Native OS Automation:</strong> Manipulate Windows desktop windows, click buttons, input text, dispatch hotkeys, and interact with the system taskbar.</li>
          <li><strong>Computer Vision & OCR:</strong> Capture desktop screens, detect window boundaries, and extract textual content via Tesseract OCR.</li>
          <li><strong>Multi-Agent Goal Decomposition:</strong> Break down complex user goals into verifiable sub-tasks and delegate to specialized domain agents.</li>
          <li><strong>Contextual Long-Term Memory:</strong> Store conversation logs, extract semantic facts, and retrieve memories using SQLite FTS5 BM25 search.</li>
          <li><strong>Cryptographic Security Gate:</strong> Enforce PIN-hash authentication for privileged system actions (file deletion, app kill, registry changes).</li>
          <li><strong>Automated Application Discovery:</strong> Continuously index installed Windows software and system utilities via the Windows Registry.</li>
          <li><strong>Continuous Personalization:</strong> Adapt to user slang (Hinglish), frequently used applications, and acoustic pitch patterns over time.</li>
          <li><strong>Proactive Telemetry & Self-Healing:</strong> Monitor CPU/RAM consumption and autonomously retry failed automation actions.</li>
        </ul>

        <h2 class="sub-title">3.2 Non-Functional Requirements</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 25%;">Requirement</th>
              <th style="width: 75%;">Implementation Consideration</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Security & Privacy</td>
              <td>100% on-device air-gapped execution; salted SHA-256 PIN hashing; local database encryption; automated PII redaction from logs.</td>
            </tr>
            <tr>
              <td>Latency & Performance</td>
              <td>Sub-250ms voice transcription via faster-whisper; AVX2-accelerated GGUF CPU token streaming; lightweight PyWebView container.</td>
            </tr>
            <tr>
              <td>Reliability & Fault Tolerance</td>
              <td>Centralized error handling; traceback parsing; self-healing GUI retry loops; defensive parameter bounds checking.</td>
            </tr>
            <tr>
              <td>Usability & Ergonomics</td>
              <td>Dark-mode glassmorphic React interface; hands-free voice radar; non-intrusive floating desktop widget mode.</td>
            </tr>
            <tr>
              <td>Modularity & Extensibility</td>
              <td>Decoupled 11 Flask service blueprints; lazy-loaded multi-agent registry; pluggable tool definition schemas.</td>
            </tr>
            <tr>
              <td>Storage Efficiency</td>
              <td>Zero-dependency SQLite databases; FTS5 virtual tables; automated Ebbinghaus memory fading to prevent database bloat.</td>
            </tr>
          </tbody>
        </table>

        <h2 class="sub-title">3.3 Hardware and Software Requirements</h2>
        <p>
          <strong>Hardware Requirements:</strong> A modern personal computer equipped with an Intel Core i5/i7 (8th Gen+) or AMD 
          Ryzen 5/7 quad-core x64 processor supporting AVX2 instructions; minimum 8 GB of RAM (16 GB recommended for concurrent 
          8B GGUF model execution); 20 GB of free SSD storage; standard audio microphone input and speaker/headphone output.
        </p>
        <p>
          <strong>Software Requirements:</strong> Windows 10/11 64-bit operating system; Python 3.10+ runtime; Node.js 18+ and npm; 
          Tesseract-OCR 5+ binary; C++ Build Tools (MSVC for compiling llama-cpp-python); SQLite3; modern Chromium web engine 
          (Microsoft Edge / PyWebView); Git version control.
        </p>
      </div>
      <div class="page-footer">Page 7</div>
    </div>
    """
    pages.append(p7)

    # =========================================================================
    # PAGE 8: 4. SYSTEM ARCHITECTURE AND DESIGN (PART 1)
    # =========================================================================
    p8 = """
    <div class="page" id="page-8">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">4. SYSTEM ARCHITECTURE AND DESIGN</h1>

        <h2 class="sub-title">4.1 Architectural Overview</h2>
        <p>
          PULSAR follows a layered, edge-native client-server architecture designed for zero cloud reliance and optimal desktop responsiveness. 
          The presentation layer is composed of a React 18 frontend packaged into a native desktop container using PyWebView. It communicates 
          with the local Python Flask API Gateway via RESTful endpoints and bidirectional Socket.IO WebSockets. The gateway orchestrates 
          the cognitive engine, multi-agent dispatchers, sensory perception pipelines, and native Windows automation drivers.
        </p>
        <p style="margin-bottom: 6pt;">
          The layered architecture of the completed system is illustrated in Figure 4.1.
        </p>

        <div class="fig-box">
          <svg width="580" height="410" viewBox="0 0 580 410" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <!-- Layer 1: Client Layer -->
            <rect x="20" y="10" width="540" height="60" rx="8" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.3"/>
            <text x="35" y="28" font-size="10.5" font-weight="bold" fill="#2b6cb0">CLIENT LAYER</text>
            <rect x="130" y="24" width="230" height="36" rx="5" fill="#ffffff" stroke="#3182ce" stroke-width="1"/>
            <text x="245" y="40" font-size="9" font-weight="bold" fill="#2d3748" text-anchor="middle">React 18 + Vite Frontend Dashboard</text>
            <text x="245" y="52" font-size="7.5" fill="#718096" text-anchor="middle">(Voice Radar, Telemetry, Chat UI, App Grid)</text>

            <rect x="380" y="24" width="165" height="36" rx="5" fill="#ffffff" stroke="#3182ce" stroke-width="1"/>
            <text x="462" y="40" font-size="9" font-weight="bold" fill="#2d3748" text-anchor="middle">Native PyWebView Container</text>
            <text x="462" y="52" font-size="7.5" fill="#718096" text-anchor="middle">(Frameless Desktop Window)</text>

            <line x1="290" y1="70" x2="290" y2="88" stroke="#2c3e50" stroke-width="1.5" stroke-dasharray="3,3"/>

            <!-- Layer 2: API Gateway Layer -->
            <rect x="20" y="88" width="540" height="68" rx="8" fill="#f7fafc" stroke="#4a5568" stroke-width="1.3"/>
            <text x="35" y="106" font-size="10.5" font-weight="bold" fill="#2d3748">APPLICATION & API GATEWAY LAYER</text>
            
            <rect x="35" y="114" width="140" height="34" rx="5" fill="#ffffff" stroke="#4a5568" stroke-width="1"/>
            <text x="105" y="128" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">Flask REST API Gateway</text>
            <text x="105" y="140" font-size="7" fill="#718096" text-anchor="middle">(/api/v1 Architecture)</text>

            <rect x="185" y="114" width="150" height="34" rx="5" fill="#ffffff" stroke="#4a5568" stroke-width="1"/>
            <text x="260" y="128" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">Socket.IO WebSockets</text>
            <text x="260" y="140" font-size="7" fill="#718096" text-anchor="middle">(Real-Time Voice & Events)</text>

            <rect x="345" y="114" width="200" height="34" rx="5" fill="#ffffff" stroke="#4a5568" stroke-width="1"/>
            <text x="445" y="128" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">11 Modular Service Blueprints</text>
            <text x="445" y="140" font-size="7" fill="#718096" text-anchor="middle">(Voice, Apps, Automation, Memory, etc.)</text>

            <line x1="290" y1="156" x2="290" y2="174" stroke="#2c3e50" stroke-width="1.5"/>

            <!-- Layer 3: Cognitive & Multi-Agent Layer -->
            <rect x="20" y="174" width="540" height="74" rx="8" fill="#f0fff4" stroke="#38a169" stroke-width="1.3"/>
            <text x="35" y="192" font-size="10.5" font-weight="bold" fill="#276749">COGNITIVE & MULTI-AGENT LAYER</text>

            <rect x="35" y="200" width="165" height="40" rx="5" fill="#ffffff" stroke="#38a169" stroke-width="1"/>
            <text x="117" y="215" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">Central Agent Dispatcher</text>
            <text x="117" y="227" font-size="7" fill="#718096" text-anchor="middle">Intent Parsing & Task Routing</text>
            <text x="117" y="236" font-size="7" fill="#718096" text-anchor="middle">27 Continuous Learning Systems</text>

            <rect x="210" y="200" width="160" height="40" rx="5" fill="#ffffff" stroke="#38a169" stroke-width="1"/>
            <text x="290" y="215" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">Multi-Agent Swarm Registry</text>
            <text x="290" y="227" font-size="7" fill="#718096" text-anchor="middle">Productivity, File, Web,</text>
            <text x="290" y="236" font-size="7" fill="#718096" text-anchor="middle">Student & Autonomous Agents</text>

            <rect x="380" y="200" width="165" height="40" rx="5" fill="#ffffff" stroke="#38a169" stroke-width="1"/>
            <text x="462" y="215" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">Quantized LLM Engine</text>
            <text x="462" y="227" font-size="7" fill="#718096" text-anchor="middle">Llama 3.1 8B Q4_K_M GGUF</text>
            <text x="462" y="236" font-size="7" fill="#718096" text-anchor="middle">AVX2 CPU Inference (llama-cpp)</text>

            <line x1="290" y1="248" x2="290" y2="266" stroke="#2c3e50" stroke-width="1.5"/>

            <!-- Layer 4: Perception & Automation Layer -->
            <rect x="20" y="266" width="540" height="66" rx="8" fill="#faf5ff" stroke="#805ad5" stroke-width="1.3"/>
            <text x="35" y="284" font-size="10.5" font-weight="bold" fill="#6b46c1">PERCEPTION & OS AUTOMATION LAYER</text>

            <rect x="35" y="292" width="160" height="33" rx="5" fill="#ffffff" stroke="#805ad5" stroke-width="1"/>
            <text x="115" y="306" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">Voice Processing Pipeline</text>
            <text x="115" y="318" font-size="7" fill="#718096" text-anchor="middle">faster-whisper STT + eSpeak/TTS</text>

            <rect x="205" y="292" width="160" height="33" rx="5" fill="#ffffff" stroke="#805ad5" stroke-width="1"/>
            <text x="285" y="306" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">Desktop Vision & OCR</text>
            <text x="285" y="318" font-size="7" fill="#718096" text-anchor="middle">Screen Grab + Tesseract 5 OCR</text>

            <rect x="375" y="292" width="170" height="33" rx="5" fill="#ffffff" stroke="#805ad5" stroke-width="1"/>
            <text x="460" y="306" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">OS Actuation Engine</text>
            <text x="460" y="318" font-size="7" fill="#718096" text-anchor="middle">PyWin32, PyAutoGUI, Registry</text>

            <line x1="290" y1="332" x2="290" y2="350" stroke="#2c3e50" stroke-width="1.5"/>

            <!-- Layer 5: Data & Persistence Layer -->
            <rect x="20" y="350" width="540" height="52" rx="8" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.3"/>
            <text x="30" y="380" font-size="8.5" font-weight="bold" fill="#c05621">PERSISTENCE &amp; DATA LAYER</text>

            <rect x="205" y="358" width="165" height="34" rx="5" fill="#ffffff" stroke="#dd6b20" stroke-width="1"/>
            <text x="287" y="372" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">SQLite Cluster (7 Databases)</text>
            <text x="287" y="384" font-size="7" fill="#718096" text-anchor="middle">memory.db, chat_history.db, FTS5 Indexing</text>

            <rect x="380" y="358" width="170" height="34" rx="5" fill="#ffffff" stroke="#dd6b20" stroke-width="1"/>
            <text x="465" y="372" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">Knowledge Graph &amp; Config</text>
            <text x="465" y="384" font-size="7" fill="#718096" text-anchor="middle">Neo4j Semantic Triples + .env Secrets</text>
          </svg>
          <div class="fig-cap">Figure 4.1: Layered system architecture of PULSAR</div>
        </div>

        <h2 class="sub-title">4.2 Major Components</h2>
        <p>
          <strong>React Frontend:</strong> Renders visual dashboards, voice radar animation, chat logs, and hardware telemetry.<br/>
          <strong>Flask API Gateway:</strong> High-throughput REST & WebSocket server exposing modular routes across 11 blueprints.<br/>
          <strong>Quantized LLM Engine:</strong> Local CPU inference pipeline running Llama 3.1 8B Instruct via llama-cpp-python.<br/>
          <strong>Multi-Agent Orchestrator:</strong> Decomposes compound goals and allocates execution to specialized sub-agents.<br/>
          <strong>Perception Engine:</strong> Streaming faster-whisper speech recognition, acoustic emotion analyzer, and Tesseract OCR.<br/>
          <strong>OS Automation Controller:</strong> Manages window handles, mouse clicks, keystrokes, and registry software indexing.<br/>
          <strong>SQLite FTS5 Memory Core:</strong> Stores conversational facts and documents with BM25 full-text search.
        </p>
      </div>
      <div class="page-footer">Page 8</div>
    </div>
    """
    pages.append(p8)

    # =========================================================================
    # PAGE 9: 4.3 DATA FLOW & 4.4 SECURITY DESIGN
    # =========================================================================
    p9 = """
    <div class="page" id="page-9">
      <div class="page-border"></div>
      <div>
        <h2 class="sub-title" style="margin-top: 0;">4.3 Data Flow</h2>
        <ol style="margin-bottom: 6pt;">
          <li>The user initiates an interaction via microphone audio stream, desktop text prompt, or keyboard shortcut.</li>
          <li>Perception modules transcribe speech (faster-whisper) or capture screen context (Tesseract OCR).</li>
          <li>The Flask API Gateway validates the incoming request payload and checks active session headers.</li>
          <li>If the request involves privileged OS operations (e.g., file deletion), the PIN Gate verifies the salted PIN hash.</li>
          <li>The Central Dispatcher classifies the intent, prompts local GGUF models, and coordinates sub-agent execution.</li>
          <li>The OS Automation Controller executes Win32 system actions or writes generated output.</li>
          <li>Execution results are indexed into SQLite FTS5 memory, learning metrics are updated, and voice/UI feedback is returned.</li>
        </ol>

        <p style="margin-bottom: 4pt;">
          Figure 4.2 illustrates how a typical request traverses the system, including authorization gates and error rejection paths.
        </p>

        <div class="fig-box">
          <svg width="580" height="340" viewBox="0 0 580 340" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <defs>
              <marker id="arr2" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
                <polygon points="0 0, 7 2.5, 0 5" fill="#2c3e50" />
              </marker>
            </defs>

            <!-- User Action -->
            <rect x="180" y="10" width="220" height="30" rx="15" fill="#2d3748"/>
            <text x="290" y="29" font-size="9.5" font-weight="bold" fill="#ffffff" text-anchor="middle">User Action: Voice Stream / REST API</text>

            <line x1="290" y1="40" x2="290" y2="60" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr2)"/>

            <!-- Auth Decision -->
            <polygon points="290,60 370,82 290,104 210,82" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="290" y="80" font-size="8.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Valid Session /</text>
            <text x="290" y="90" font-size="7.5" fill="#7b341e" text-anchor="middle">Active User?</text>

            <line x1="370" y1="82" x2="430" y2="82" stroke="#c0392b" stroke-width="1.3" marker-end="url(#arr2)"/>
            <text x="395" y="76" font-size="8" font-weight="bold" fill="#c0392b">No</text>
            <rect x="430" y="68" width="110" height="28" rx="5" fill="#fff5f5" stroke="#e53e3e" stroke-width="1"/>
            <text x="485" y="85" font-size="8.5" font-weight="bold" fill="#c53030" text-anchor="middle">401 Unauthorized</text>

            <line x1="290" y1="104" x2="290" y2="126" stroke="#27ae60" stroke-width="1.3" marker-end="url(#arr2)"/>
            <text x="296" y="117" font-size="8" font-weight="bold" fill="#27ae60">Yes</text>

            <!-- Privileged PIN Decision -->
            <polygon points="290,126 370,148 290,170 210,148" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="290" y="146" font-size="8.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Privileged Action</text>
            <text x="290" y="156" font-size="7.5" fill="#7b341e" text-anchor="middle">& Valid PIN?</text>

            <line x1="370" y1="148" x2="430" y2="148" stroke="#c0392b" stroke-width="1.3" marker-end="url(#arr2)"/>
            <text x="395" y="142" font-size="8" font-weight="bold" fill="#c0392b">No</text>
            <rect x="430" y="134" width="110" height="28" rx="5" fill="#fff5f5" stroke="#e53e3e" stroke-width="1"/>
            <text x="485" y="151" font-size="8.5" font-weight="bold" fill="#c53030" text-anchor="middle">403 Forbidden</text>

            <line x1="290" y1="170" x2="290" y2="192" stroke="#27ae60" stroke-width="1.3" marker-end="url(#arr2)"/>
            <text x="296" y="183" font-size="8" font-weight="bold" fill="#27ae60">Yes</text>

            <!-- Intent & Validation Decision -->
            <polygon points="290,192 370,214 290,236 210,214" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="290" y="212" font-size="8.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Valid Intent &</text>
            <text x="290" y="222" font-size="7.5" fill="#7b341e" text-anchor="middle">Parameters?</text>

            <line x1="370" y1="214" x2="430" y2="214" stroke="#c0392b" stroke-width="1.3" marker-end="url(#arr2)"/>
            <text x="395" y="208" font-size="8" font-weight="bold" fill="#c0392b">No</text>
            <rect x="430" y="200" width="110" height="28" rx="5" fill="#fff5f5" stroke="#e53e3e" stroke-width="1"/>
            <text x="485" y="217" font-size="8.5" font-weight="bold" fill="#c53030" text-anchor="middle">400 Validation Error</text>

            <line x1="290" y1="236" x2="290" y2="258" stroke="#27ae60" stroke-width="1.3" marker-end="url(#arr2)"/>
            <text x="296" y="249" font-size="8" font-weight="bold" fill="#27ae60">Yes</text>

            <!-- Execution Step -->
            <rect x="150" y="258" width="280" height="34" rx="6" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="290" y="272" font-size="8.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Dispatcher Invokes Sub-Agent & OS Tool</text>
            <text x="290" y="284" font-size="7.5" fill="#4a5568" text-anchor="middle">Win32 Actuation / GGUF CPU Token Stream / FTS5 Logging</text>

            <line x1="290" y1="292" x2="290" y2="308" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr2)"/>

            <!-- Response Node -->
            <rect x="180" y="308" width="220" height="26" rx="13" fill="#e6fffa" stroke="#319795" stroke-width="1.2"/>
            <text x="290" y="325" font-size="9" font-weight="bold" fill="#234e52" text-anchor="middle">JSON Response + Voice Audio Returned</text>
          </svg>
          <div class="fig-cap">Figure 4.2: Request processing and cognitive routing flow</div>
        </div>

        <h2 class="sub-title">4.4 Security Design</h2>
        <p>
          PULSAR enforces an air-gapped security model. All neural network inference executes strictly on the local machine 
          with zero external network transmission of user prompts. Privileged OS operations (file deletion, app termination, 
          registry modifications) require strict PIN-hash verification against the salted `PIN_HASH` environment variable. Local 
          databases and configuration files are encrypted using `SECURITY_KEY`. Furthermore, a local Named Entity Recognition (NER) 
          filter scrubs sensitive passwords and personal identifiers (PII) before any telemetry or logs are written to disk.
        </p>
      </div>
      <div class="page-footer">Page 9</div>
    </div>
    """
    pages.append(p9)

    # =========================================================================
    # PAGE 10: 5. MODULE DESCRIPTION (PART 1)
    # =========================================================================
    p10 = """
    <div class="page" id="page-10">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">5. MODULE DESCRIPTION</h1>

        <h2 class="sub-title">5.1 Authentication and Privileged Access Module</h2>
        <p>
          The Authentication and Privileged Access Module secures the local system against unauthorized execution. It manages 
          session authentication, role-based access control, and high-privilege confirmation. Commands that modify filesystem 
          structures, terminate background tasks, or inspect secure credentials trigger an elevation request requiring the user's 
          cryptographic PIN.
        </p>
        <p style="margin-bottom: 4pt;">
          The authentication and privileged elevation workflow is summarized in Figure 5.1.
        </p>

        <div class="fig-box">
          <svg width="560" height="350" viewBox="0 0 560 350" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <defs>
              <marker id="arr3" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
                <polygon points="0 0, 7 2.5, 0 5" fill="#2c3e50" />
              </marker>
            </defs>

            <rect x="180" y="10" width="200" height="30" rx="15" fill="#2d3748"/>
            <text x="280" y="29" font-size="9.5" font-weight="bold" fill="#ffffff" text-anchor="middle">User Submits Command</text>

            <line x1="280" y1="40" x2="280" y2="60" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr3)"/>

            <polygon points="280,60 365,84 280,108 195,84" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="280" y="82" font-size="8.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Requires Elevated</text>
            <text x="280" y="92" font-size="7.5" fill="#2b6cb0" text-anchor="middle">Privilege / PIN?</text>

            <!-- Branch: No -> Direct Execution -->
            <line x1="195" y1="84" x2="90" y2="84" stroke="#27ae60" stroke-width="1.3"/>
            <line x1="90" y1="84" x2="90" y2="255" stroke="#27ae60" stroke-width="1.3"/>
            <line x1="90" y1="255" x2="195" y2="255" stroke="#27ae60" stroke-width="1.3" marker-end="url(#arr3)"/>
            <text x="140" y="78" font-size="8" font-weight="bold" fill="#27ae60">No (Standard Command)</text>

            <!-- Branch: Yes -> Prompt PIN -->
            <line x1="280" y1="108" x2="280" y2="130" stroke="#dd6b20" stroke-width="1.3" marker-end="url(#arr3)"/>
            <text x="286" y="121" font-size="8" font-weight="bold" fill="#dd6b20">Yes</text>

            <rect x="190" y="130" width="180" height="34" rx="6" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="280" y="145" font-size="8.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Prompt for Security PIN</text>
            <text x="280" y="156" font-size="7.5" fill="#7b341e" text-anchor="middle">Hash Comparison against PIN_HASH</text>

            <line x1="280" y1="164" x2="280" y2="186" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr3)"/>

            <polygon points="280,186 360,208 280,230 200,208" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="280" y="206" font-size="8.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Hash Match</text>
            <text x="280" y="216" font-size="7.5" fill="#7b341e" text-anchor="middle">Successful?</text>

            <!-- Failed PIN -->
            <line x1="360" y1="208" x2="430" y2="208" stroke="#c0392b" stroke-width="1.3" marker-end="url(#arr3)"/>
            <text x="390" y="202" font-size="8" font-weight="bold" fill="#c0392b">No</text>
            <rect x="430" y="194" width="115" height="30" rx="5" fill="#fff5f5" stroke="#e53e3e" stroke-width="1"/>
            <text x="487" y="207" font-size="8" font-weight="bold" fill="#c53030" text-anchor="middle">Access Denied (403)</text>
            <text x="487" y="217" font-size="7" fill="#c53030" text-anchor="middle">Security Alert Logged</text>

            <!-- Successful PIN -->
            <line x1="280" y1="230" x2="280" y2="255" stroke="#27ae60" stroke-width="1.3" marker-end="url(#arr3)"/>
            <text x="286" y="244" font-size="8" font-weight="bold" fill="#27ae60">Yes</text>

            <!-- Execution -->
            <rect x="195" y="255" width="170" height="36" rx="6" fill="#e6fffa" stroke="#319795" stroke-width="1.2"/>
            <text x="280" y="271" font-size="8.5" font-weight="bold" fill="#234e52" text-anchor="middle">Grant Execution Token</text>
            <text x="280" y="283" font-size="7.5" fill="#285e61" text-anchor="middle">Execute Privileged Win32 Action</text>

            <line x1="280" y1="291" x2="280" y2="310" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr3)"/>

            <rect x="200" y="310" width="160" height="26" rx="13" fill="#2d3748"/>
            <text x="280" y="327" font-size="9" font-weight="bold" fill="#ffffff" text-anchor="middle">Action Completed & Logged</text>
          </svg>
          <div class="fig-cap">Figure 5.1: Authentication and privileged command execution flow</div>
        </div>

        <h2 class="sub-title">5.2 Multi-Agent Orchestration Module</h2>
        <p>
          Governed by a central Dispatcher and Agent Registry, this module coordinates autonomous sub-agents:
        </p>
        <ul>
          <li><strong>Productivity Agent:</strong> Manages calendar schedules, alarms, reminders, and daily briefing tasks.</li>
          <li><strong>File Manager Agent:</strong> Performs directory analysis, batch file renaming, duplicate removal, and file classification.</li>
          <li><strong>Communication Agent:</strong> Drafts emails, parses inbox threads, and generates context-aware message responses.</li>
          <li><strong>Research & Student Agent:</strong> Summarizes research papers, extracts technical formulas, and queries local RAG stores.</li>
          <li><strong>Creative & Audio Agent:</strong> Coordinates offline speech synthesis, audio volume scaling, and Spotify controls.</li>
          <li><strong>Autonomous Agent:</strong> Passively monitors background desktop activity and proposes proactive workflow shortcuts.</li>
        </ul>

        <h2 class="sub-title">5.3 Offline LLM Inference & Cognitive Engine</h2>
        <p>
          The cognitive reasoning core executes a fine-tuned Llama 3.1 8B Instruct model quantized to Q4_K_M GGUF format via 
          llama-cpp-python. By utilizing optimized CPU vector instructions (AVX2), the system produces real-time streaming tokens 
          with negligible latency while consuming under 6.5 GB of system RAM.
        </p>
      </div>
      <div class="page-footer">Page 10</div>
    </div>
    """
    pages.append(p10)

    # =========================================================================
    # PAGE 11: 5. MODULE DESCRIPTION (PART 2)
    # =========================================================================
    p11 = """
    <div class="page" id="page-11">
      <div class="page-border"></div>
      <div>
        <h2 class="sub-title" style="margin-top: 0;">5.4 Multimodal Perception (Voice & Vision) Module</h2>
        <p>
          This module supplies real-time sensory capabilities. The audio pipeline utilizes `faster-whisper` with dynamic chunking 
          to provide sub-250ms streaming transcription directly from microphone feeds. An acoustic emotion tracking subsystem evaluates 
          voice stream pitch variance and root-mean-square energy to assess user urgency or frustration prior to text analysis. 
          The computer vision subsystem captures desktop frames, detects active window bounding boxes, and uses Tesseract 5 OCR 
          to read on-screen error dialogs, software text, and taskbar icons.
        </p>

        <h2 class="sub-title">5.5 Operating System Automation & Tool Execution Module</h2>
        <p>
          The automation controller translates abstract cognitive decisions into concrete Windows API operations. Utilizing 
          `pywin32` and `pywinauto`, it manipulates native window handles, shifts application focus, issues mouse clicks, and simulates 
          keyboard shortcuts. An automated App Discovery subsystem scans the Windows Registry and Start Menu to index installed 
          executables without requiring hard-coded paths.
        </p>
        <p style="margin-bottom: 4pt;">
          Figure 5.2 outlines the autonomous task decomposition and self-healing execution pipeline.
        </p>

        <div class="fig-box">
          <svg width="560" height="420" viewBox="0 0 560 420" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <defs>
              <marker id="arr4" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
                <polygon points="0 0, 7 2.5, 0 5" fill="#2c3e50" />
              </marker>
              <marker id="arr-green4" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
                <polygon points="0 0, 7 2.5, 0 5" fill="#27ae60" />
              </marker>
              <marker id="arr-red4" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
                <polygon points="0 0, 7 2.5, 0 5" fill="#c0392b" />
              </marker>
            </defs>

            <!-- Goal Ingestion -->
            <rect x="180" y="10" width="200" height="28" rx="14" fill="#2d3748"/>
            <text x="280" y="28" font-size="9" font-weight="bold" fill="#ffffff" text-anchor="middle">High-Level User Goal Received</text>

            <line x1="280" y1="38" x2="280" y2="58" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr4)"/>

            <!-- Goal Decomposition -->
            <rect x="170" y="58" width="220" height="34" rx="6" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="280" y="73" font-size="8.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Goal Decomposition Engine</text>
            <text x="280" y="84" font-size="7.5" fill="#4a5568" text-anchor="middle">Breaks goal into Directed Acyclic Graph (DAG)</text>

            <line x1="280" y1="92" x2="280" y2="112" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr4)"/>

            <!-- Step Assignment -->
            <rect x="170" y="112" width="220" height="34" rx="6" fill="#f0fff4" stroke="#38a169" stroke-width="1.2"/>
            <text x="280" y="127" font-size="8.5" font-weight="bold" fill="#276749" text-anchor="middle">Sub-Agent & Tool Allocation</text>
            <text x="280" y="138" font-size="7.5" fill="#4a5568" text-anchor="middle">Extracts deterministic execution parameters</text>

            <line x1="280" y1="146" x2="280" y2="166" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr4)"/>

            <!-- Pre-Execution Check -->
            <polygon points="280,166 360,188 280,210 200,188" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="280" y="185" font-size="8" font-weight="bold" fill="#7b341e" text-anchor="middle">Pre-Conditions</text>
            <text x="280" y="195" font-size="7" fill="#7b341e" text-anchor="middle">Satisfied?</text>

            <line x1="360" y1="188" x2="430" y2="188" stroke="#c0392b" stroke-width="1.3" marker-end="url(#arr-red4)"/>
            <text x="390" y="182" font-size="8" font-weight="bold" fill="#c0392b">No</text>
            <rect x="430" y="174" width="115" height="28" rx="5" fill="#fff5f5" stroke="#e53e3e" stroke-width="1"/>
            <text x="487" y="191" font-size="7.5" font-weight="bold" fill="#c53030" text-anchor="middle">Resolve Missing State</text>

            <line x1="280" y1="210" x2="280" y2="232" stroke="#27ae60" stroke-width="1.3" marker-end="url(#arr-green4)"/>
            <text x="286" y="222" font-size="8" font-weight="bold" fill="#27ae60">Yes</text>

            <!-- Tool Invocation -->
            <rect x="170" y="232" width="220" height="34" rx="6" fill="#faf5ff" stroke="#805ad5" stroke-width="1.2"/>
            <text x="280" y="247" font-size="8.5" font-weight="bold" fill="#6b46c1" text-anchor="middle">Execute Win32 / Tool Action</text>
            <text x="280" y="258" font-size="7.5" fill="#4a5568" text-anchor="middle">App focus, click coordinates, keystrokes</text>

            <line x1="280" y1="266" x2="280" y2="286" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr4)"/>

            <!-- State Verification -->
            <polygon points="280,286 360,308 280,330 200,308" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="280" y="305" font-size="8" font-weight="bold" fill="#7b341e" text-anchor="middle">Screen State</text>
            <text x="280" y="315" font-size="7" fill="#7b341e" text-anchor="middle">Verified by OCR?</text>

            <!-- Self-Healing loop -->
            <path d="M 200 308 L 100 308 L 100 249 L 170 249" fill="none" stroke="#c0392b" stroke-width="1.3" marker-end="url(#arr-red4)"/>
            <text x="125" y="300" font-size="7.5" font-weight="bold" fill="#c0392b">No: Self-Heal</text>
            <text x="125" y="288" font-size="6.5" fill="#742a2a">(Recalculate Bounds)</text>

            <line x1="280" y1="330" x2="280" y2="352" stroke="#27ae60" stroke-width="1.3" marker-end="url(#arr-green4)"/>
            <text x="286" y="342" font-size="8" font-weight="bold" fill="#27ae60">Yes</text>

            <!-- All Steps Done? -->
            <rect x="180" y="352" width="200" height="28" rx="6" fill="#e6fffa" stroke="#319795" stroke-width="1.2"/>
            <text x="280" y="369" font-size="8" font-weight="bold" fill="#234e52" text-anchor="middle">Advance Step / Mark DAG Complete</text>

            <line x1="280" y1="380" x2="280" y2="396" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr4)"/>

            <rect x="200" y="396" width="160" height="22" rx="11" fill="#2d3748"/>
            <text x="280" y="411" font-size="8.5" font-weight="bold" fill="#ffffff" text-anchor="middle">Task Completed Successfully</text>
          </svg>
          <div class="fig-cap">Figure 5.2: Autonomous task decomposition and execution workflow</div>
        </div>

        <h2 class="sub-title">5.6 Continuous Learning & Memory Module</h2>
        <p>
          Unlike static models, PULSAR continuously evolves to match user habits. It couples an SQLite FTS5 index with 27 
          programmatic learning systems to handle personalization without destructive weight catastrophic forgetting.
        </p>
      </div>
      <div class="page-footer">Page 11</div>
    </div>
    """
    pages.append(p11)

    # =========================================================================
    # PAGE 12: 5. MODULE DESCRIPTION (PART 3)
    # =========================================================================
    p12 = """
    <div class="page" id="page-12">
      <div class="page-border"></div>
      <div>
        <h2 class="sub-title" style="margin-top: 0;">5.6 Continuous Learning & Memory Module (Continued)</h2>
        <p>
          The system implements 27 distinct programmatic learning paradigms that adapt dynamically:
        </p>
        <ul>
          <li><strong>Active & Reinforcement Learning:</strong> Proactively queries the user when commands are ambiguous and continuously tunes routing policies based on thumbs up/down user feedback.</li>
          <li><strong>Intent Drift & Hinglish Adaptation:</strong> Detects vocabulary shifts and automatically updates intent classifiers when users employ colloquial Indian phrases or code-mixed Hindi-English syntax.</li>
          <li><strong>Contextual Memory Fading:</strong> Incorporates an Ebbinghaus forgetting curve algorithm to decay the retrieval weight of stale information while strengthening frequently recalled facts.</li>
          <li><strong>Contrastive Learning:</strong> Distinguishes between semantically similar operating system commands (e.g., closing an application tab vs. terminating the host application process).</li>
          <li><strong>Semantic Knowledge Graphing:</strong> Extracts subject-predicate-object triples from daily interactions, storing them in local SQLite graphs for multi-hop relational reasoning.</li>
          <li><strong>Self-Supervised Log Learning:</strong> Ingests background OS execution logs to automatically discover application failure patterns and common user workflow sequences.</li>
          <li><strong>Zero-Shot Transfer Application:</strong> Generalizes document scraping logic to unfamiliar desktop application windows without requiring pre-trained profiles.</li>
        </ul>

        <h2 class="sub-title">5.7 Contextual Telemetry & Proactive Diagnostics Module</h2>
        <p>
          Operating silently in the background, this module continuously observes desktop context and health:
        </p>
        <ul>
          <li><strong>Active Window Tracker:</strong> Monitors foreground window focus changes. When a user transitions from a code editor to a web browser, PULSAR preemptively surfaces relevant documentation or bookmarks.</li>
          <li><strong>Hardware Constraint Learning:</strong> Continuously inspects CPU, RAM, and battery state via `psutil`. If heavy workloads (e.g., video rendering or gaming) are detected, background indexing is throttled.</li>
          <li><strong>Self-Healing Code Recovery:</strong> When an automation action encounters a runtime exception (such as a moved button or altered UI handle), the engine parses the traceback, analyzes the screen via OCR, recalibrates screen coordinates, and safely retries.</li>
          <li><strong>Trust-Scaling Personality Engine:</strong> Dynamically modulates AI verbosity and conversational tone from strict, concise confirmations for new users to colloquial, proactive assistance as trust metrics scale.</li>
        </ul>
      </div>
      <div class="page-footer">Page 12</div>
    </div>
    """
    pages.append(p12)

    # =========================================================================
    # PAGE 13: 6. DATABASE DESIGN (PART 1)
    # =========================================================================
    p13 = """
    <div class="page" id="page-13">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">6. DATABASE DESIGN</h1>

        <h2 class="sub-title">6.1 Database Technology</h2>
        <p>
          PULSAR utilizes a zero-dependency, local SQLite database architecture. Instead of relying on a monolithic, resource-heavy 
          database server or external cloud vectors, data persistence is partitioned into seven dedicated SQLite database files stored 
          in the `data/` directory. Partitioning prevents table locking contention between concurrent background worker threads. 
          Furthermore, high-throughput text recall is achieved via SQLite's `FTS5` (Full-Text Search 5) virtual tables, providing 
          sub-15ms BM25 ranking without external vector engine overhead.
        </p>

        <h2 class="sub-title">6.2 Major Entities and Databases</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 20%;">Database / Entity</th>
              <th style="width: 25%;">Database File</th>
              <th style="width: 55%;">Purpose and Key Fields</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>App Usage</td>
              <td><code>app_usage.db</code></td>
              <td>Tracks application launches, paths, usage frequencies, categories, and last-used timestamps. Used by K-Means behavioral scheduler.</td>
            </tr>
            <tr>
              <td>Chat History</td>
              <td><code>chat_history.db</code></td>
              <td>Stores session metadata (session_id, started_at, message_count) and individual user/assistant chat messages with token counts.</td>
            </tr>
            <tr>
              <td>Conversation AI</td>
              <td><code>conversation_ai.db</code></td>
              <td>Maintains serialized conversational context, active multi-turn goals, and persistent AI personality parameters.</td>
            </tr>
            <tr>
              <td>Enhanced Learning</td>
              <td><code>enhanced_learning.db</code></td>
              <td>Stores active learning prompts, user feedback rewards (RLHF), intent drift training pairs, and classification benchmarks.</td>
            </tr>
            <tr>
              <td>Language Data</td>
              <td><code>language_data.db</code></td>
              <td>Stores multilingual preferences, localized vocabulary mappings, and colloquial Hinglish token translations.</td>
            </tr>
            <tr>
              <td>Memory Core</td>
              <td><code>memory.db</code></td>
              <td>Core long-term knowledge repository utilizing SQLite FTS5 virtual tables for BM25 retrieval, semantic triples, and decay scores.</td>
            </tr>
            <tr>
              <td>Personal Knowledge</td>
              <td><code>personal_knowledge.db</code></td>
              <td>User-defined rules, custom macros, application shortcut profiles, and private notes.</td>
            </tr>
            <tr>
              <td>Chain History</td>
              <td><code>chain_history.db</code></td>
              <td>Maintains execution traces of multi-step autonomous plans, tool DAGs, step verification statuses, and self-healing logs.</td>
            </tr>
          </tbody>
        </table>

        <h2 class="sub-title">6.3 Agent Task State Model</h2>
        <p>
          Every autonomous task generated by the system transitions through a formal, deterministic state machine. Tasks initialize 
          as <code>PENDING</code>, proceed to <code>PARSING</code> and <code>PLANNING</code>, and enter <code>AWAITING_PIN</code> 
          if privileged OS actions are detected. Upon elevation, the task enters <code>EXECUTING</code> and <code>VERIFYING</code>. 
          If execution encounters unexpected UI changes, the state transitions to <code>SELF_HEALING</code> to recalculate parameters, 
          preventing unhandled failures.
        </p>
      </div>
      <div class="page-footer">Page 13</div>
    </div>
    """
    pages.append(p13)

    # =========================================================================
    # PAGE 14: 6. DATABASE DESIGN (PART 2)
    # =========================================================================
    p14 = """
    <div class="page" id="page-14">
      <div class="page-border"></div>
      <div>
        <p style="font-size: 10pt; line-height: 1.35; margin-bottom: 6pt;">
          The permitted transitions between agent task execution states are shown in Figure 6.1.
        </p>

        <div class="fig-box">
          <svg width="560" height="210" viewBox="0 0 560 210" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <defs>
              <marker id="arr5" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
                <polygon points="0 0, 7 2.5, 0 5" fill="#2c3e50" />
              </marker>
              <marker id="arr-red5" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
                <polygon points="0 0, 7 2.5, 0 5" fill="#c0392b" />
              </marker>
            </defs>

            <!-- Initial state -->
            <circle cx="25" cy="45" r="10" fill="#2d3748"/>
            <line x1="35" y1="45" x2="60" y2="45" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr5)"/>

            <rect x="60" y="30" width="75" height="30" rx="5" fill="#f7fafc" stroke="#4a5568" stroke-width="1.2"/>
            <text x="97" y="49" font-size="8.5" font-weight="bold" fill="#2d3748" text-anchor="middle">PENDING</text>

            <line x1="135" y1="45" x2="160" y2="45" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr5)"/>

            <rect x="160" y="30" width="75" height="30" rx="5" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="197" y="49" font-size="8.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">PARSING</text>

            <line x1="235" y1="45" x2="260" y2="45" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr5)"/>

            <rect x="260" y="30" width="80" height="30" rx="5" fill="#e6fffa" stroke="#319795" stroke-width="1.2"/>
            <text x="300" y="49" font-size="8.5" font-weight="bold" fill="#234e52" text-anchor="middle">PLANNING</text>

            <line x1="340" y1="45" x2="370" y2="45" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr5)"/>

            <rect x="370" y="30" width="85" height="30" rx="5" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="412" y="49" font-size="8.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">EXECUTING</text>

            <line x1="455" y1="45" x2="480" y2="45" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr5)"/>

            <!-- Completed terminal -->
            <rect x="480" y="30" width="65" height="30" rx="15" fill="#27ae60"/>
            <text x="512" y="49" font-size="8.5" font-weight="bold" fill="#ffffff" text-anchor="middle">DONE</text>

            <!-- Privileged branch -->
            <path d="M 300 60 L 300 110 L 370 110" fill="none" stroke="#dd6b20" stroke-width="1.3" marker-end="url(#arr5)"/>
            <text x="260" y="95" font-size="7.5" fill="#dd6b20" font-weight="bold">Privileged</text>

            <rect x="370" y="95" width="85" height="30" rx="5" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="412" y="114" font-size="8" font-weight="bold" fill="#7b341e" text-anchor="middle">AWAITING_PIN</text>

            <path d="M 455 110 L 470 110 L 470 70 L 412 70 L 412 60" fill="none" stroke="#27ae60" stroke-width="1.3" marker-end="url(#arr5)"/>
            <text x="475" y="95" font-size="7" fill="#27ae60" font-weight="bold">Verified</text>

            <!-- Self-Healing loop -->
            <path d="M 412 60 L 412 165 L 300 165" fill="none" stroke="#c0392b" stroke-width="1.3" marker-end="url(#arr-red5)"/>
            <text x="360" y="155" font-size="7.5" fill="#c0392b" font-weight="bold">UI Error / Offset</text>

            <rect x="200" y="150" width="100" height="30" rx="5" fill="#fff5f5" stroke="#e53e3e" stroke-width="1.2"/>
            <text x="250" y="169" font-size="8" font-weight="bold" fill="#c53030" text-anchor="middle">SELF_HEALING</text>

            <path d="M 200 165 L 120 165 L 120 70 L 260 70 L 260 60" fill="none" stroke="#3182ce" stroke-width="1.3" marker-end="url(#arr5)"/>
            <text x="125" y="125" font-size="7" fill="#3182ce" font-weight="bold">Recalibrate Bounds</text>
          </svg>
          <div class="fig-cap">Figure 6.1: Agent task and execution state transition diagram</div>
        </div>

        <h2 class="sub-title">6.4 Knowledge Graph and Memory Retention Pipeline</h2>
        <p>
          To maintain rich context without suffering from unbounded database inflation, PULSAR implements an ingestion, 
          extraction, indexing, and decay pipeline. The process is outlined in Figure 6.2.
        </p>

        <div class="fig-box">
          <svg width="560" height="230" viewBox="0 0 560 230" xmlns="http://www.w3.org/2000/svg" style="font-family: Arial, sans-serif;">
            <defs>
              <marker id="arr6" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
                <polygon points="0 0, 7 2.5, 0 5" fill="#2c3e50" />
              </marker>
            </defs>

            <rect x="15" y="15" width="150" height="42" rx="6" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="90" y="32" font-size="8.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Interaction Stream</text>
            <text x="90" y="44" font-size="7.5" fill="#4a5568" text-anchor="middle">Conversations & System Events</text>

            <line x1="165" y1="36" x2="205" y2="36" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr6)"/>

            <rect x="205" y="15" width="160" height="42" rx="6" fill="#f0fff4" stroke="#38a169" stroke-width="1.2"/>
            <text x="285" y="32" font-size="8.5" font-weight="bold" fill="#276749" text-anchor="middle">Entity & Triple Extraction</text>
            <text x="285" y="44" font-size="7.5" fill="#4a5568" text-anchor="middle">Subject-Predicate-Object Parser</text>

            <line x1="365" y1="36" x2="405" y2="36" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr6)"/>

            <rect x="405" y="15" width="140" height="42" rx="6" fill="#e6fffa" stroke="#319795" stroke-width="1.2"/>
            <text x="475" y="32" font-size="8.5" font-weight="bold" fill="#234e52" text-anchor="middle">SQLite FTS5 Storage</text>
            <text x="475" y="44" font-size="7.5" fill="#285e61" text-anchor="middle">BM25 Document Index</text>

            <path d="M 475 57 L 475 100 L 375 100" fill="none" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr6)"/>

            <rect x="205" y="80" width="170" height="42" rx="6" fill="#fffaf0" stroke="#dd6b20" stroke-width="1.2"/>
            <text x="290" y="97" font-size="8.5" font-weight="bold" fill="#7b341e" text-anchor="middle">Ebbinghaus Memory Decay</text>
            <text x="290" y="109" font-size="7.5" fill="#7b341e" text-anchor="middle">Exponential Curve Weighting</text>

            <path d="M 205 101 L 90 101 L 90 145" fill="none" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr6)"/>

            <rect x="15" y="145" width="150" height="42" rx="6" fill="#faf5ff" stroke="#805ad5" stroke-width="1.2"/>
            <text x="90" y="162" font-size="8.5" font-weight="bold" fill="#6b46c1" text-anchor="middle">Context Query Pipeline</text>
            <text x="90" y="174" font-size="7.5" fill="#553c9a" text-anchor="middle">Hybrid BM25 + Recency Ranking</text>

            <line x1="165" y1="166" x2="205" y2="166" stroke="#2c3e50" stroke-width="1.3" marker-end="url(#arr6)"/>

            <rect x="205" y="145" width="340" height="42" rx="6" fill="#ebf8ff" stroke="#3182ce" stroke-width="1.2"/>
            <text x="375" y="162" font-size="8.5" font-weight="bold" fill="#2b6cb0" text-anchor="middle">Prompt Injection & Cognitive Synthesis</text>
            <text x="375" y="174" font-size="7.5" fill="#4a5568" text-anchor="middle">Relevant episodic facts injected into Llama 3.1 8B context window</text>
          </svg>
          <div class="fig-cap">Figure 6.2: Long-term memory storage, decay scoring, and retrieval process</div>
        </div>
      </div>
      <div class="page-footer">Page 14</div>
    </div>
    """
    pages.append(p14)

    # =========================================================================
    # PAGE 15: 7. IMPLEMENTATION
    # =========================================================================
    p15 = """
    <div class="page" id="page-15">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">7. IMPLEMENTATION</h1>

        <h2 class="sub-title">7.1 Frontend Implementation</h2>
        <p>
          The frontend is implemented with React 18, TypeScript, and Vite, packaged in a lightweight Chromium instance via 
          PyWebView. It incorporates Tailwind CSS and Lucide icons to present a modern glassmorphic dark-mode interface. 
          Key frontend sections include the Voice Radar Widget (streaming audio visualizer), Conversational Assistant, 
          Multi-Agent Task Monitor, Interactive App Grid, Learning Metrics Dashboard, and Hardware Telemetry Gauge.
        </p>

        <h2 class="sub-title">7.2 Backend Implementation</h2>
        <p>
          The backend is engineered using Python 3.10+ and Flask. Rather than relying on a fragile monolithic structure, 
          routes are partitioned into 11 modular Flask Blueprints: <code>voice_bp</code>, <code>apps_bp</code>, 
          <code>automation_bp</code>, <code>learning_bp</code>, <code>memory_bp</code>, <code>ocr_bp</code>, 
          <code>web_bp</code>, <code>chat_bp</code>, <code>models_bp</code>, <code>chains_bp</code>, and <code>system_bp</code>. 
          Bidirectional Socket.IO handles low-latency event broadcasting for live transcription and agent state changes.
        </p>

        <h2 class="sub-title">7.3 Cognitive Engine & Local Inference</h2>
        <p>
          Local inference is powered by <code>llama-cpp-python</code> compiled with native AVX2 instruction sets. The assistant 
          runs a customized, instruction-tuned Llama 3.1 8B model quantized to Q4_K_M GGUF format. Deterministic tool execution 
          is enforced using strict JSON grammar constraints, ensuring the model outputs structured arguments matching 
          the parameters expected by the automation controllers.
        </p>

        <h2 class="sub-title">7.4 Native Desktop Packaging & Automation</h2>
        <p>
          Operating system actuation is implemented via <code>pywin32</code> and <code>pywinauto</code>, providing direct 
          bindings to Windows User32 and Kernel32 APIs. The platform monitors foreground window handles, detects taskbar 
          applications, and simulates hardware-level mouse clicks and keyboard events. Desktop deployment is achieved using 
          PyInstaller to bundle Python runtimes, C++ binaries, and models into an optimized standalone Windows executable.
        </p>

        <h2 class="sub-title">7.5 Deployment and Environment Configuration</h2>
        <p>
          PULSAR operates with zero cloud dependencies. System variables are managed via a local <code>.env</code> file containing 
          the salted <code>PIN_HASH</code>, local encryption <code>SECURITY_KEY</code>, and optional external API fallback keys. 
          Automated deployment scripts (<code>install.ps1</code> and <code>Start.bat</code>) verify dependencies, initialize the 
          SQLite database cluster, and launch both frontend and backend processes in a single click.
        </p>
      </div>
      <div class="page-footer">Page 15</div>
    </div>
    """
    pages.append(p15)

    # =========================================================================
    # PAGE 16: 8. TESTING AND VALIDATION (PART 1)
    # =========================================================================
    p16 = """
    <div class="page" id="page-16">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">8. TESTING AND VALIDATION</h1>

        <h2 class="sub-title">8.1 Testing Approach</h2>
        <p>
          Testing was conducted across unit, integration, and end-to-end levels to verify system reliability, responsiveness, 
          and offline autonomy. Over 42 dedicated test suites within the <code>tests/</code> directory were executed using <code>pytest</code>. 
          Testing validated local GGUF model token generation, speech transcription accuracy, Win32 window focus mechanics, 
          SQLite FTS5 query latency, and multi-agent task planning.
        </p>

        <h2 class="sub-title">8.2 Test Cases</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 32%;">Test Case</th>
              <th style="width: 52%;">Expected Result</th>
              <th style="width: 16%; text-align: center;">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>GGUF Model CPU Loading</td>
              <td>Llama 3.1 8B Q4 GGUF loads into memory within 4.5 seconds on quad-core CPU.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Real-Time Speech Recognition</td>
              <td>Streaming audio transcribed by faster-whisper with latency under 250ms.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Intent Classification</td>
              <td>Accurately classifies user command across 12 distinct intent domains.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Privileged Action PIN Gate</td>
              <td>Blocks privileged OS actions; successfully unlocks upon valid PIN entry.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Native Window Focus & Keystrokes</td>
              <td>Brings target application to foreground and enters text accurately.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Desktop Screen OCR Extraction</td>
              <td>Tesseract extracts text and bounding boxes from active desktop windows.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Multi-Agent Goal Planning</td>
              <td>Decomposes multi-step command into a sequential DAG of sub-tasks.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Hinglish Intent Drift Adaptation</td>
              <td>Correctly resolves colloquial Indian phrasing into formal automation actions.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>SQLite FTS5 Memory Recall</td>
              <td>Retrieves relevant historical facts within 15ms using BM25 ranking.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Ebbinghaus Memory Decay</td>
              <td>Deprecates older, unused memory weights according to exponential curve.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>App Registry Indexing</td>
              <td>Scans Windows Registry and indexes installed application paths.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Audio Emotion Detection</td>
              <td>Computes pitch and energy to reliably identify user frustration states.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Self-Healing Error Recovery</td>
              <td>Recalculates UI coordinates upon missed click and completes action.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
            <tr>
              <td>Air-Gapped Offline Operation</td>
              <td>All core features operate seamlessly with network interface disabled.</td>
              <td style="text-align: center; font-weight: bold; color: #27ae60;">Passed</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="page-footer">Page 16</div>
    </div>
    """
    pages.append(p16)

    # =========================================================================
    # PAGE 17: 8. TESTING AND VALIDATION (PART 2)
    # =========================================================================
    p17 = """
    <div class="page" id="page-17">
      <div class="page-border"></div>
      <div>
        <h2 class="sub-title" style="margin-top: 0;">8.3 Error Handling & Self-Healing Engine</h2>
        <p>
          PULSAR features a multi-tiered resilience architecture designed to handle ambiguous user input and dynamic desktop 
          environments without crashing. If an operating system automation action encounters an unexpected obstacle (such as a 
          minimized window or altered UI button coordinate), the Self-Healing Engine captures an updated screen frame, runs OCR 
          to recalculate target bounding boxes, and retries the action up to three times.
        </p>
        <p>
          Unhandled Python exceptions are intercepted by a centralized error middleware, logging encrypted tracebacks while 
          returning informative feedback to the user. Input validators check command parameters prior to execution, and fallback 
          classifiers prompt the user for clarification whenever intent confidence drops below established thresholds.
        </p>

        <h2 class="sub-title">8.4 Validation Result</h2>
        <p>
          The completed system was rigorously validated against comprehensive real-world desktop scenarios:
        </p>
        <ul>
          <li><strong>Autonomous Research & Summarization:</strong> Successfully parsed local PDF research papers, extracted key mathematical formulas, and generated concise executive summaries.</li>
          <li><strong>Hands-Free Workflow Automation:</strong> Demonstrated hands-free voice control to launch development environments, arrange window grids, and control music playback during active coding sessions.</li>
          <li><strong>Proactive Desktop Maintenance:</strong> Detected low disk capacity, identified duplicate downloads across multiple directories, and presented a unified cleanup confirmation prompt.</li>
          <li><strong>Computational Efficiency:</strong> Confirmed that local CPU inference maintains stable token generation rates of 12–18 tokens/second on an 8-thread CPU while holding memory consumption strictly below 6.5 GB RAM.</li>
        </ul>
        <p>
          The validation confirms that PULSAR successfully satisfies all functional, architectural, and security requirements 
          formulated in the initial engineering specifications.
        </p>
      </div>
      <div class="page-footer">Page 17</div>
    </div>
    """
    pages.append(p17)

    # =========================================================================
    # PAGE 18: 9. RESULTS, BENEFITS AND LIMITATIONS
    # =========================================================================
    p18 = """
    <div class="page" id="page-18">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">9. RESULTS, BENEFITS AND LIMITATIONS</h1>

        <h2 class="sub-title">9.1 Results</h2>
        <p>
          The completed PULSAR application provides a robust, fully offline AI desktop assistant for Windows. All planned 
          components—including local quantized GGUF inference, faster-whisper streaming speech transcription, Tesseract desktop 
          vision, 11 modular Flask blueprints, 27 continuous learning systems, and PyWin32 automation—are fully operational 
          and integrated into a cohesive desktop platform.
        </p>

        <h2 class="sub-title">9.2 Benefits</h2>
        <ul>
          <li><strong>Absolute Privacy & Data Sovereignty:</strong> All voice, screen, and text processing executes entirely on-device; no private telemetry or keystrokes are transmitted across external networks.</li>
          <li><strong>Zero Ongoing Costs:</strong> Eliminates recurring API token costs and subscription billing associated with cloud-hosted commercial AI assistants.</li>
          <li><strong>Direct OS Actuation:</strong> Bridges conversational reasoning with actual desktop capabilities, enabling hands-free control of native applications and file systems.</li>
          <li><strong>Multimodal Natural Interaction:</strong> Enables users to communicate seamlessly via speech, text prompts, or on-screen visual triggers.</li>
          <li><strong>Continuous Personalization:</strong> Adapts to user linguistic habits (including Hinglish slang) and daily workflow patterns without requiring cloud model retraining.</li>
          <li><strong>Low-Overhead Persistent Memory:</strong> Utilizes lightweight SQLite FTS5 databases for instant memory retrieval without demanding dedicated vector servers.</li>
        </ul>

        <h2 class="sub-title">9.3 Limitations</h2>
        <ul>
          <li><strong>CPU Compute Dependency:</strong> Generation speed on local models is directly tied to host processor clock speed and AVX2 instruction availability.</li>
          <li><strong>Windows Platform Lock-In:</strong> Automation controllers rely extensively on native Win32 accessibility APIs; cross-platform Linux and macOS support remains experimental.</li>
          <li><strong>DPI Scaling Sensitivity:</strong> Complex multi-monitor configurations with disparate DPI scaling factors can occasionally introduce coordinate offsets during visual clicking.</li>
          <li><strong>Memory Footprint:</strong> Loading the 8B quantized model requires approximately 5.8 to 6.5 GB of system RAM, limiting concurrent operation on systems with 8 GB or less.</li>
        </ul>

        <h2 class="sub-title">9.4 Academic Significance</h2>
        <p>
          The project demonstrates the practical integration of edge machine learning, quantized transformer architectures, 
          low-level operating system APIs, digital speech processing, asynchronous web gateways, and full-text search algorithms 
          into a cohesive, production-grade software engineering system.
        </p>
      </div>
      <div class="page-footer">Page 18</div>
    </div>
    """
    pages.append(p18)

    # =========================================================================
    # PAGE 19: 10. FUTURE SCOPE AND CONCLUSION
    # =========================================================================
    p19 = """
    <div class="page" id="page-19">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">10. FUTURE SCOPE AND CONCLUSION</h1>

        <h2 class="sub-title">10.1 Future Scope</h2>
        <ul>
          <li><strong>Cross-Platform OS Support:</strong> Develop dedicated automation drivers for Linux (via X11/Wayland) and macOS (via Accessibility APIs) to achieve full platform portability.</li>
          <li><strong>On-Device Vision-Language Model:</strong> Fine-tune a lightweight local VLM (such as Moondream or Qwen2-VL) to replace OCR with direct pixel-based visual navigation.</li>
          <li><strong>Decentralized Device Synchronization:</strong> Implement peer-to-peer encrypted synchronization of memory databases across the user's desktop, laptop, and mobile devices.</li>
          <li><strong>Dynamic LoRA Adapter Hot-Swapping:</strong> Enable instantaneous switching of specialized LoRA adapters for specialized domains such as software engineering, legal review, and creative writing.</li>
          <li><strong>Few-Shot Voice Cloning:</strong> Integrate local few-shot neural voice synthesis to allow the assistant to communicate with personalized, custom vocal characteristics.</li>
        </ul>

        <h2 class="sub-title">10.2 Conclusion</h2>
        <p>
          PULSAR successfully bridges the gap between passive conversational language models and active desktop computing. 
          By combining quantized local large language models with native Windows automation, multimodal sensory perception, 
          and continuous learning algorithms, it transforms the operating system from a passive workspace into an intelligent, 
          collaborative partner.
        </p>
        <p>
          The project demonstrates that private, powerful, and agentic AI assistants can operate reliably on standard consumer 
          hardware without sacrificing user privacy or incurring costly cloud subscriptions. The modular architecture established 
          in this work provides a solid foundation for future expansions in edge intelligence, cross-platform automation, and 
          autonomous computing.
        </p>

        <h2 class="sub-title">10.3 Learning Outcomes</h2>
        <p>
          The project provided extensive practical experience in local LLM quantization, C++ bindings via llama-cpp, 
          asynchronous micro-service architecture using Flask and WebSockets, modern frontend engineering with React and Vite, 
          low-level Windows Win32 API programming, digital speech signal processing, full-text database indexing, and 
          rigorous end-to-end system testing.
        </p>
      </div>
      <div class="page-footer">Page 19</div>
    </div>
    """
    pages.append(p19)

    # =========================================================================
    # PAGE 20: 11. REFERENCES AND APPENDIX
    # =========================================================================
    p20 = """
    <div class="page" id="page-20">
      <div class="page-border"></div>
      <div>
        <h1 class="sec-title">11. REFERENCES AND APPENDIX</h1>

        <h2 class="sub-title">11.1 References</h2>
        <ol style="margin-bottom: 6pt;">
          <li>Meta AI, "Llama 3 Herd of Models: Architecture, Quantization, and Capabilities," Technical Report, 2024.</li>
          <li>Gerganov, G., "llama.cpp: Efficient Port of LLaMA Model Architecture in C/C++," GitHub Repository, 2024.</li>
          <li>Radford, A. et al., "Robust Speech Recognition via Large-Scale Weak Supervision," OpenAI Whisper, 2023.</li>
          <li>Smith, R., "An Overview of the Tesseract OCR Engine," 9th International Conference on Document Analysis, 2007.</li>
          <li>Pallets Projects, "Flask Documentation: Modular Web Applications with Blueprints," 2024.</li>
          <li>Meta Open Source, "React 18 Documentation: Concurrent Features and Interactive UI State," 2024.</li>
          <li>SQLite Consortium, "SQLite FTS5 Extension: Full-Text Search and BM25 Ranking Algorithm," 2024.</li>
          <li>Hammond, M., "Python for Windows Extensions (pywin32): Accessing Native Win32 Subsystems," 2023.</li>
          <li>Al-Sweigart, A., "PyAutoGUI: Cross-Platform GUI Automation Module for Python," 2024.</li>
          <li>OWASP Foundation, "Top 10 Privacy and Security Considerations for Local Agentic AI Applications," 2024.</li>
        </ol>

        <h2 class="sub-title">11.2 Major Project Routes and Functional Areas</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 25%;">Area</th>
              <th style="width: 75%;">Major Routes and Functions</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Authentication & PIN</td>
              <td><code>/api/auth/*</code>, PIN hash elevation, session verification, rate limiting, token refresh.</td>
            </tr>
            <tr>
              <td>Cognitive Engine</td>
              <td><code>/api/local_ai/*</code>, <code>/api/chat</code>, GGUF model load/unload, token streaming, context formatting.</td>
            </tr>
            <tr>
              <td>Voice & Audio</td>
              <td><code>/api/voice/*</code>, streaming faster-whisper STT, offline pyttsx3/eSpeak TTS, audio emotion tracking.</td>
            </tr>
            <tr>
              <td>Screen Vision & OCR</td>
              <td><code>/api/screen/analyze</code>, <code>/api/ocr/*</code>, desktop frame capture, Tesseract text extraction.</td>
            </tr>
            <tr>
              <td>Windows Automation</td>
              <td><code>/api/apps/*</code>, <code>/api/automation/execute</code>, window focus, keystrokes, mouse events, taskbar.</td>
            </tr>
            <tr>
              <td>Memory & Learning</td>
              <td><code>/api/learning/*</code>, <code>/api/memory/*</code>, SQLite FTS5 RAG search, Hinglish adaptation, habit logs.</td>
            </tr>
            <tr>
              <td>System Telemetry</td>
              <td><code>/api/system/stats</code>, <code>/api/startup/*</code>, CPU/RAM monitoring, active window watcher.</td>
            </tr>
          </tbody>
        </table>

        <h2 class="sub-title">11.3 Technology Summary</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 25%;">Layer</th>
              <th style="width: 75%;">Technology Stack</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Frontend</td>
              <td>React 18, TypeScript, Vite, Tailwind CSS, Lucide React, PyWebView</td>
            </tr>
            <tr>
              <td>Backend Gateway</td>
              <td>Python 3.10+, Flask, Flask-SocketIO, 11 Service Blueprints</td>
            </tr>
            <tr>
              <td>Cognitive / LLM</td>
              <td>Llama 3.1 8B Instruct (Q4_K_M GGUF), llama-cpp-python, AVX2 CPU vector acceleration</td>
            </tr>
            <tr>
              <td>Perception (Voice/Vision)</td>
              <td>faster-whisper, pyttsx3, eSpeak-ng, Tesseract OCR 5, OpenCV, Pillow</td>
            </tr>
            <tr>
              <td>OS Actuation</td>
              <td>pywin32, pywinauto, pyautogui, Windows Registry API</td>
            </tr>
            <tr>
              <td>Persistence & Search</td>
              <td>SQLite 3 with FTS5 virtual tables, Neo4j Graph DB, JSON storage</td>
            </tr>
            <tr>
              <td>Packaging & Deploy</td>
              <td>PyInstaller, PyWebView native window, PowerShell & Batch scripts (install.ps1, Start.bat)</td>
            </tr>
          </tbody>
        </table>

        <div style="text-align: center; margin-top: 12pt; font-size: 10pt; font-weight: bold; letter-spacing: 0.5px;">
          End of Synopsis<br/>
          <span style="font-size: 11pt; letter-spacing: 1.5px;">PULSAR</span>
        </div>
      </div>
      <div class="page-footer">Page 20</div>
    </div>
    """
    pages.append(p20)

    # Combine into full HTML
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
## A Native OS Automation and Multi-Modal Agentic AI Assistant for Windows

**SYNOPSIS OF MAJOR PROJECT**  
of  
**Bachelor of Technology**  
in  
**Computer Science & Engineering**  

### By
| S.No. | Student Name | Roll Number | Branch and Section |
| :---: | :---: | :---: | :---: |
| 1 | Diwakar Singh | 2301650100004 | Computer Science & Engineering |

**Kanpur Institute of Technology, Kanpur**  
**Dr. A.P.J. Abdul Kalam Technical University, Lucknow**  
**Academic Session: 2026–27**  

---

## DECLARATION
We hereby declare that this submission is our own work and that, to the best of our knowledge and belief, it contains no material previously published or written by another person nor material which to a substantial extent has been accepted for the award of any other degree or diploma by the university or other institute of higher learning, except where due acknowledgement has been made in the text.

**Signature:** _________________________________________  
**Name:** Diwakar Singh  
**Roll No:** 2301650100004  
**Date:** ________________________  

**Approved By:**  
**Rahul Singh**  
Head of Department  
Computer Science and Engineering  
KIT, KANPUR  
**Signature:** _________________________________________  

---

## TABLE OF CONTENTS
| No. | Particulars | Page |
| :---: | :--- | :---: |
| 1. | Introduction | 4 |
| 2. | Objectives and System Study | 5 |
| 3. | Requirement Analysis | 7 |
| 4. | System Architecture and Design | 8 |
| 5. | Module Description | 10 |
| 6. | Database Design | 13 |
| 7. | Implementation | 15 |
| 8. | Testing and Validation | 16 |
| 9. | Results, Benefits and Limitations | 18 |
| 10. | Future Scope and Conclusion | 19 |
| 11. | References and Appendix | 20 |

---

## 1. INTRODUCTION

### 1.1 Background
Personal computing workflows have expanded dramatically in scope and complexity. Modern users routinely operate across dozens of simultaneous desktop windows, disparate software utilities, web browsers, code editors, and file repositories. While modern Large Language Models (LLMs) have demonstrated remarkable conversational and cognitive capabilities, the overwhelming majority of existing AI assistants remain constrained within remote web browsers and sandboxed cloud environments. They act as passive conversational advisors rather than active operating system actuating agents.

PULSAR was developed as a unified, offline, multi-modal operating system automation platform for Windows. It connects natural language and voice interaction directly to the underlying operating system environment, allowing users to automate desktop applications, organize files, inspect system processes, perform real-time screen OCR, and retrieve long-term context entirely on-device without exposing sensitive data to cloud servers.

### 1.2 Problem Statement
Traditional commercial AI assistants suffer from three fundamental architectural shortcomings:
1. **Privacy Risks:** Private system state, typed documents, and personal queries are transmitted over the public internet to third-party data centers.
2. **Lack of OS Integration:** They cannot click desktop buttons, switch active windows, launch installed software, or manage local directory hierarchies.
3. **High Latency & Costs:** Recurring subscription fees and network round-trip latencies degrade real-time hands-free voice usability.

PULSAR addresses these challenges by implementing an air-gapped, zero-leakage desktop assistant architecture leveraging 4-bit quantized local GGUF models on consumer CPUs, real-time speech recognition, and native Windows Win32 APIs for safe, deterministic automation.

### 1.3 Need for the System
- 100% offline edge execution ensuring absolute privacy, data ownership, and zero telemetry leakage.
- Direct Windows OS automation (GUI navigation, window management, keystrokes, and registry inspection).
- Real-time multimodal sensory perception combining fast streaming voice STT, TTS, and desktop OCR.
- Deterministic multi-agent task planning to break down complex goals into safe, verifiable execution steps.
- Continuous personalization using 27 programmatic learning paradigms that adapt to user habits and slang.
- Zero-dependency persistent memory utilizing SQLite FTS5 full-text search with zero cloud footprint.

### 1.4 Scope of the Project
The scope includes a dual-engine architecture featuring a React + Vite + TypeScript desktop interface, a modular Flask API gateway with 11 domain blueprints, local Q4_K_M GGUF Llama 3.1 8B CPU inference, real-time speech recognition via faster-whisper, desktop vision and Tesseract OCR, PyWin32 automation drivers, SQLite database clusters, PIN-based cryptographic security, and automated system diagnostics.

---

## 2. OBJECTIVES AND SYSTEM STUDY

### 2.1 Objectives
1. Develop a high-performance offline AI desktop agent natively integrated into the Windows OS environment.
2. Implement local quantized LLM inference (Llama 3.1 8B Q4_K_M GGUF) operating efficiently on consumer CPUs.
3. Construct a multi-agent orchestration dispatcher for natural language goal decomposition and negotiation.
4. Integrate real-time streaming speech recognition (faster-whisper) with acoustic emotion tracking and TTS.
5. Provide visual desktop perception through window boundary tracking, screen capture, and Tesseract OCR.
6. Build an OS automation engine using PyWin32 and PyAutoGUI for hands-free software navigation and control.
7. Implement 27 continuous learning paradigms to dynamically adapt to user vocabulary, Hinglish slang, and habits.
8. Provide zero-dependency long-term memory retrieval using SQLite FTS5 BM25 search and semantic graphs.
9. Enforce strict PIN-based cryptographic authorization for privileged system, filesystem, and process controls.
10. Package the complete system into a responsive native Windows desktop application using PyWebView.

### 2.2 Existing System
| Area | Typical Approach | Limitation |
| :--- | :--- | :--- |
| **OS Control** | Web-based chatbots (ChatGPT, Claude) | Sandboxed inside browser; cannot interact with native apps or files. |
| **Data Privacy** | Cloud LLM REST APIs | User prompts, files, and system data are sent to remote corporate servers. |
| **Latency & Cost** | Pay-per-token cloud subscriptions | High network latency hampers voice interaction; ongoing monthly fees. |
| **Context & Memory** | Ephemeral session histories | Loss of context across desktop reboots; expensive context window scaling. |
| **Desktop Macros** | Rigid RPA / AutoHotkey scripts | Fragile to UI layout changes; incapable of cognitive reasoning or error recovery. |

### 2.3 Proposed System
PULSAR bridges the gap between neural cognitive reasoning and deterministic OS execution. The system runs an edge-quantized cognitive engine coupled with a multi-agent dispatcher, perception pipelines, and native Windows automation drivers. Complex user requests are autonomously decomposed into sequential sub-tasks, validated through security checks, executed directly against native Windows applications, and remembered across sessions via local SQLite databases.

*(Refer to Figure 2.1 in the generated PDF for the full interaction workflow diagram).*

---

## 3. REQUIREMENT ANALYSIS

### 3.1 Functional Requirements
- **Natural Language & Voice Processing:** Ingest real-time microphone streams, transcribe audio using faster-whisper, and parse natural text intents.
- **Edge LLM Inference:** Execute 4-bit quantized GGUF models on CPU without requiring external APIs, cloud compute, or active internet connections.
- **Native OS Automation:** Manipulate Windows desktop windows, click buttons, input text, dispatch hotkeys, and interact with the system taskbar.
- **Computer Vision & OCR:** Capture desktop screens, detect window boundaries, and extract textual content via Tesseract OCR.
- **Multi-Agent Goal Decomposition:** Break down complex user goals into verifiable sub-tasks and delegate to specialized domain agents.
- **Contextual Long-Term Memory:** Store conversation logs, extract semantic facts, and retrieve memories using SQLite FTS5 BM25 search.
- **Cryptographic Security Gate:** Enforce PIN-hash authentication for privileged system actions (file deletion, app kill, registry changes).
- **Automated Application Discovery:** Continuously index installed Windows software and system utilities via the Windows Registry.
- **Continuous Personalization:** Adapt to user slang (Hinglish), frequently used applications, and acoustic pitch patterns over time.
- **Proactive Telemetry & Self-Healing:** Monitor CPU/RAM consumption and autonomously retry failed automation actions.

### 3.2 Non-Functional Requirements
| Requirement | Implementation Consideration |
| :--- | :--- |
| **Security & Privacy** | 100% on-device air-gapped execution; salted SHA-256 PIN hashing; local database encryption; automated PII redaction from logs. |
| **Latency & Performance** | Sub-250ms voice transcription via faster-whisper; AVX2-accelerated GGUF CPU token streaming; lightweight PyWebView container. |
| **Reliability & Fault Tolerance** | Centralized error handling; traceback parsing; self-healing GUI retry loops; defensive parameter bounds checking. |
| **Usability & Ergonomics** | Dark-mode glassmorphic React interface; hands-free voice radar; non-intrusive floating desktop widget mode. |
| **Modularity & Extensibility** | Decoupled 11 Flask service blueprints; lazy-loaded multi-agent registry; pluggable tool definition schemas. |
| **Storage Efficiency** | Zero-dependency SQLite databases; FTS5 virtual tables; automated Ebbinghaus memory fading to prevent database bloat. |

### 3.3 Hardware and Software Requirements
- **Hardware:** Intel Core i5/i7 (8th Gen+) or AMD Ryzen 5/7 quad-core x64 processor supporting AVX2; minimum 8 GB of RAM (16 GB recommended); 20 GB free SSD storage; standard microphone and speakers.
- **Software:** Windows 10/11 64-bit OS; Python 3.10+; Node.js 18+ & npm; Tesseract-OCR 5+; C++ Build Tools (MSVC); SQLite3; Microsoft Edge / PyWebView runtime; Git.

---

## 4. SYSTEM ARCHITECTURE AND DESIGN

### 4.1 Architectural Overview
PULSAR follows a layered, edge-native client-server architecture:
- **Client Layer:** React 18 + Vite dashboard hosted in a frameless native PyWebView window.
- **API Gateway Layer:** Flask REST API with 11 domain blueprints and bidirectional Socket.IO WebSockets.
- **Cognitive & Multi-Agent Layer:** Central Dispatcher, Multi-Agent Swarm Registry, and Llama 3.1 8B Q4_K_M GGUF model via llama-cpp-python.
- **Perception & Automation Layer:** faster-whisper STT, offline TTS, Tesseract OCR, and PyWin32/PyAutoGUI automation.
- **Data & Persistence Layer:** 7 isolated SQLite databases with FTS5 full-text indexing, Neo4j semantic graph, and encrypted configurations.

### 4.2 Major Components
- **React Frontend:** Voice radar, chat assistant, telemetry monitors, and settings.
- **Flask Gateway:** Modular service endpoints routing requests and maintaining WebSockets.
- **Cognitive Engine:** Quantized LLM inference executing with native AVX2 instructions.
- **Multi-Agent Orchestrator:** Task planning, sub-agent delegation, and tool invocation.
- **Perception Pipeline:** Real-time audio stream listener and desktop OCR vision.
- **OS Controller:** Native Windows Win32 API window, mouse, and keyboard actuator.
- **SQLite FTS5 Core:** Sub-15ms BM25 long-term conversational memory store.

### 4.3 Data Flow
1. User provides input via microphone stream, text box, or global hotkey.
2. Sensory modules transcribe speech or extract screen text.
3. Gateway validates session tokens and payload parameters.
4. If privileged OS actions are requested, PIN Gate validates against `PIN_HASH`.
5. Dispatcher prompts Llama 3.1 8B GGUF model and plans sub-tasks.
6. Automation engine executes Win32 system actions.
7. Results are logged to SQLite memory, learning models are updated, and voice/UI feedback is returned.

### 4.4 Security Design
Air-gapped local execution guarantees zero external telemetry. Privileged actions require salted SHA-256 PIN hashing (`PIN_HASH`). Database and config files are encrypted with `SECURITY_KEY`. Local Named Entity Recognition (NER) redacts passwords and PII from execution logs before saving to disk.

---

## 5. MODULE DESCRIPTION

### 5.1 Authentication and Privileged Access Module
Enforces access control and defends system resources. Commands modifying filesystem hierarchies, terminating tasks, or accessing sensitive credentials require cryptographic PIN verification.

### 5.2 Multi-Agent Orchestration Module
Coordinates specialized autonomous agents:
- **Productivity Agent:** Schedules calendar events, reminders, and daily briefings.
- **File Manager Agent:** Categorizes files, batch renames, and eliminates duplicate downloads.
- **Communication Agent:** Composes emails, summarizes messages, and drafts replies.
- **Research & Student Agent:** Summarizes academic papers, extracts equations, and queries RAG facts.
- **Creative & Audio Agent:** Manages voice synthesis, volume controls, and media playback.
- **Autonomous Agent:** Passively observes user workflows and suggests proactive automations.

### 5.3 Offline LLM Inference & Cognitive Engine
Executes a fine-tuned, 4-bit quantized Llama 3.1 8B Instruct model (Q4_K_M GGUF) via llama-cpp-python, maintaining 12–18 tokens/sec on quad-core CPUs under 6.5 GB RAM.

### 5.4 Multimodal Perception (Voice & Vision) Module
Integrates `faster-whisper` for sub-250ms streaming transcription, an acoustic emotion tracker analyzing voice pitch and volume, and Tesseract 5 OCR for reading desktop windows.

### 5.5 Operating System Automation & Tool Execution Module
Translates cognitive goals into Windows API actions via `pywin32` and `pywinauto`. Features automated application discovery scanning the Windows Registry and Start Menu.

### 5.6 Continuous Learning & Memory Module
Implements 27 distinct programmatic learning systems including Active Learning, Intent Drift Adaptation for Hinglish slang, Ebbinghaus Memory Fading, and Contrastive Learning.

### 5.7 Contextual Telemetry & Proactive Diagnostics Module
Monitors active window focus shifts, tracks CPU/RAM via `psutil`, performs self-healing GUI recovery on failed clicks, and modulates AI personality dynamically.

---

## 6. DATABASE DESIGN

### 6.1 Database Technology
Lightweight local SQLite3 cluster partitioned into 7 databases. Utilizes SQLite's FTS5 extension for BM25 ranking without external vector database servers.

### 6.2 Major Entities and Databases
| Database | File | Purpose |
| :--- | :--- | :--- |
| **App Usage** | `app_usage.db` | Application launch frequencies, paths, and last-used timestamps. |
| **Chat History** | `chat_history.db` | Session metadata and message logs with token counts. |
| **Conversation AI** | `conversation_ai.db` | Context state, ongoing multi-turn goals, and personality parameters. |
| **Enhanced Learning** | `enhanced_learning.db` | Training samples, RLHF weights, intent drift logs, and feedback. |
| **Language Data** | `language_data.db` | Multilingual preferences, Hinglish slang mappings, and vocabulary caches. |
| **Memory Core** | `memory.db` | Long-term knowledge repository with SQLite FTS5 indexing and decay scores. |
| **Personal Knowledge** | `personal_knowledge.db` | User-defined rules, shortcut macros, and custom notes. |
| **Chain History** | `chain_history.db` | Multi-step execution traces, tool DAGs, and self-healing logs. |

### 6.3 Agent Task State Model
Tasks transition through `PENDING` -> `PARSING` -> `PLANNING` -> (`AWAITING_PIN` if privileged) -> `EXECUTING` -> `VERIFYING` -> `COMPLETED`. If errors occur, the state switches to `SELF_HEALING` to recalculate parameters.

### 6.4 Knowledge Graph and Memory Retention Pipeline
Interactions undergo entity/triple extraction, storage into SQLite FTS5 tables, exponential decay weighting via the Ebbinghaus forgetting curve, and dynamic injection into the LLM prompt.

---

## 7. IMPLEMENTATION

### 7.1 Frontend Implementation
React 18, TypeScript, Vite, Tailwind CSS, Lucide icons, and PyWebView native container. Includes Voice Radar, Assistant chat, task execution monitors, and hardware widgets.

### 7.2 Backend Implementation
Python 3.10+ Flask gateway structured into 11 Blueprints with Socket.IO bidirectional event broadcasting.

### 7.3 Cognitive Engine & Local Inference
Llama 3.1 8B Instruct (Q4_K_M GGUF) via `llama-cpp-python` with AVX2 CPU vector optimizations and strict JSON grammar constraints.

### 7.4 Native Desktop Packaging & Automation
`pywin32`, `pywinauto`, and `pyautogui` for native Windows API interaction; PyInstaller for packaging into a standalone executable.

### 7.5 Deployment and Environment Configuration
Configured via `.env` with `PIN_HASH` and `SECURITY_KEY`. Automated installation and startup scripts (`install.ps1` and `Start.bat`).

---

## 8. TESTING AND VALIDATION

### 8.1 Testing Approach
Comprehensive testing across 42+ test suites in `tests/` using `pytest`. Tested model loading, voice latency, Win32 window focus, and SQLite FTS5 search.

### 8.2 Test Cases (Summary)
- Local GGUF Model Loading: **Passed**
- Real-Time Speech Recognition (<250ms): **Passed**
- Intent Classification (12 domains): **Passed**
- Privileged Action PIN Gate: **Passed**
- Window Focus & Keystrokes: **Passed**
- Screen OCR Extraction: **Passed**
- Multi-Agent Task Planning: **Passed**
- Hinglish Intent Drift Adaptation: **Passed**
- SQLite FTS5 Memory Retrieval (<15ms): **Passed**
- Memory Decay Weighting: **Passed**
- App Registry Indexing: **Passed**
- Audio Emotion Detection: **Passed**
- Self-Healing Error Recovery: **Passed**
- Offline Air-Gapped Operation: **Passed**

### 8.3 Error Handling & Self-Healing Engine
Self-Healing engine recalculates UI coordinates via OCR upon missed clicks. Exception middleware logs encrypted tracebacks and returns clear user feedback.

### 8.4 Validation Result
System demonstrated reliable operation across automated research paper summarization, hands-free voice desktop control, and proactive maintenance with memory usage under 6.5 GB RAM.

---

## 9. RESULTS, BENEFITS AND LIMITATIONS

### 9.1 Results
Fully functional offline AI desktop assistant with local GGUF inference, streaming speech recognition, desktop OCR vision, 11 service blueprints, and native Win32 automation.

### 9.2 Benefits
- 100% on-device privacy and data ownership.
- Zero subscription fees or per-token charges.
- Direct Windows OS desktop application and file automation.
- Multimodal natural voice, text, and visual interaction.
- Personalization with 27 learning systems and Hinglish support.
- Zero-overhead persistent memory using SQLite FTS5.

### 9.3 Limitations
- Inference speed depends on host CPU core count and AVX capability.
- Windows-specific Win32 automation hooks (Linux/macOS experimental).
- Multi-monitor DPI scaling variations can occasionally affect visual click coordinates.
- System RAM requirement of ~6 GB for running the quantized 8B model.

### 9.4 Academic Significance
Synthesizes edge computing, quantized language models, OS API engineering, speech processing, and human-computer interaction into a production-ready system.

---

## 10. FUTURE SCOPE AND CONCLUSION

### 10.1 Future Scope
- Cross-platform automation support for Linux and macOS.
- On-device lightweight Vision-Language Model (VLM) for direct pixel navigation.
- Peer-to-peer encrypted synchronization across personal devices.
- Dynamic LoRA adapter hot-swapping for specialized tasks.
- Local few-shot voice cloning.

### 10.2 Conclusion
PULSAR transforms the personal computer from a passive machine into an active, intelligent partner. By uniting local quantized LLMs with native Windows automation, multimodal perception, and continuous learning, it proves that private, autonomous AI assistants can operate reliably on consumer hardware without compromising privacy or incurring cloud costs.

### 10.3 Learning Outcomes
Mastery in local LLM quantization, C++ bindings, asynchronous Flask architectures, React frontend development, low-level Windows APIs, speech processing, and software validation.

---

## 11. REFERENCES AND APPENDIX

### 11.1 References
1. Meta AI, "Llama 3 Herd of Models: Architecture, Quantization, and Capabilities," 2024.
2. Gerganov, G., "llama.cpp: Efficient Port of LLaMA in C/C++," GitHub, 2024.
3. Radford, A. et al., "Robust Speech Recognition via Large-Scale Weak Supervision," OpenAI, 2023.
4. Smith, R., "An Overview of the Tesseract OCR Engine," ICDAR, 2007.
5. Pallets Projects, "Flask Documentation: Blueprints & Architecture," 2024.
6. Meta Open Source, "React 18 Documentation: Concurrent Features," 2024.
7. SQLite Consortium, "SQLite FTS5 Extension: Full-Text Search," 2024.
8. Hammond, M., "Python for Windows Extensions (pywin32)," 2023.
9. Al-Sweigart, A., "PyAutoGUI: Cross-Platform GUI Automation," 2024.
10. OWASP Foundation, "Top 10 Considerations for Agentic AI Applications," 2024.

### 11.2 Major Project Routes
- **Authentication & PIN:** `/api/auth/*`
- **Cognitive Engine:** `/api/local_ai/*`, `/api/chat`
- **Voice & Audio:** `/api/voice/*`
- **Screen & OCR:** `/api/screen/analyze`, `/api/ocr/*`
- **Windows Automation:** `/api/apps/*`, `/api/automation/execute`
- **Memory & Learning:** `/api/learning/*`, `/api/memory/*`
- **System Telemetry:** `/api/system/stats`, `/api/startup/*`

### 11.3 Technology Summary
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, PyWebView
- **Backend:** Python 3.10+, Flask, Socket.IO, 11 Blueprints
- **Cognitive Model:** Llama 3.1 8B Instruct (Q4_K_M GGUF via llama-cpp-python)
- **Voice/Vision:** faster-whisper, pyttsx3, Tesseract OCR 5, OpenCV
- **OS Automation:** pywin32, pywinauto, pyautogui
- **Persistence:** SQLite3 (FTS5), Neo4j Graph, JSON
- **Packaging:** PyInstaller, PyWebView, Batch/PowerShell scripts

**End of Synopsis**  
**PULSAR**
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
