export interface CommandAnalysis {
    isMultiStep: boolean;
    isParallel: boolean;
    stepCount: number;
    segments: string[];
}

const SEQUENTIAL_CONNECTORS = /\b(?:and\s+then|after\s+that|then|next|afterwards|followed\s+by|aur\s+phir|aur\s+fir|iske\s+baad|uske\s+baad|phir|fir)\b/i;
const PARALLEL_MARKERS = /\b(?:simultaneously|in\s+parallel|at\s+the\s+same\s+time|concurrently|saath\s+mein|ek\s+saath)\b/i;
const NUMBERED_LIST = /(?:^|\n)\s*\d+[.)]\s+\S/;

/**
 * Quote-aware multi-step analyzer for command input preview.
 * Matches backend tokenizer conventions (&&, ;, ->, =>, newlines, numbered lists,
 * sequential/parallel connectors) while ignoring delimiters inside quotes or URLs.
 */
export function analyzeCommandInput(rawText: string): CommandAnalysis {
    const trimmed = (rawText || '').trim();
    if (!trimmed) {
        return { isMultiStep: false, isParallel: false, stepCount: 0, segments: [] };
    }

    // Mask double/single quoted spans and URLs so internal punctuation/keywords don't trigger false splits
    const maskedChars: string[] = [];
    let quote: '"' | "'" | null = null;
    let escaped = false;

    for (let i = 0; i < trimmed.length; i++) {
        const ch = trimmed[i];
        if (escaped) {
            maskedChars.push(' ');
            escaped = false;
            continue;
        }
        if (ch === '\\' && quote) {
            maskedChars.push(' ');
            escaped = true;
            continue;
        }
        if (ch === '"' || ch === "'") {
            if (!quote) {
                quote = ch;
            } else if (quote === ch) {
                quote = null;
            }
            maskedChars.push(' ');
            continue;
        }
        maskedChars.push(quote ? ' ' : ch);
    }

    const unquoted = maskedChars.join('').replace(/https?:\/\/\S+/gi, ' __URL__ ');
    const isParallel = PARALLEL_MARKERS.test(unquoted);

    // Split along structural delimiters outside quotes
    let parts = unquoted
        .split(/(?:\s*&&\s*|\s*;\s*|\s*->\s*|\s*=>\s*|\r?\n+)/)
        .map((s) => s.trim())
        .filter(Boolean);

    // Further check numbered lists or sequential connectors if still a single chunk or mixed
    const expanded: string[] = [];
    for (const part of parts) {
        if (NUMBERED_LIST.test(part)) {
            const numbered = part
                .split(/\s*(?=\b\d+[.)]\s+)/)
                .map((s) => s.replace(/^\d+[.)]\s*/, '').trim())
                .filter(Boolean);
            expanded.push(...numbered);
            continue;
        }
        if (SEQUENTIAL_CONNECTORS.test(part)) {
            const seqSplit = part
                .split(/\s+(?:and\s+then|after\s+that|then|next|afterwards|followed\s+by|aur\s+phir|aur\s+fir|iske\s+baad|uske\s+baad|phir|fir)\s+/i)
                .map((s) => s.trim())
                .filter(Boolean);
            expanded.push(...seqSplit);
            continue;
        }
        expanded.push(part);
    }

    parts = expanded.filter((s) => s.length > 0);
    const stepCount = parts.length;
    const isMultiStep = stepCount > 1;

    return {
        isMultiStep,
        isParallel,
        stepCount,
        segments: parts,
    };
}
