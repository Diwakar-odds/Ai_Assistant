import { describe, it, expect } from 'vitest';
import { analyzeCommandInput } from '../commandUtils';

describe('analyzeCommandInput', () => {
    it('returns empty analysis for blank or whitespace input', () => {
        const res = analyzeCommandInput('   ');
        expect(res.isMultiStep).toBe(false);
        expect(res.stepCount).toBe(0);
        expect(res.segments).toEqual([]);
        expect(res.isParallel).toBe(false);
    });

    it('identifies single simple command', () => {
        const res = analyzeCommandInput('open visual studio code');
        expect(res.isMultiStep).toBe(false);
        expect(res.stepCount).toBe(1);
        expect(res.segments).toEqual(['open visual studio code']);
        expect(res.isParallel).toBe(false);
    });

    it('does NOT split delimiters inside double quotes or single quotes', () => {
        const res1 = analyzeCommandInput('echo "hello && world"');
        expect(res1.isMultiStep).toBe(false);
        expect(res1.stepCount).toBe(1);

        const res2 = analyzeCommandInput('search \'AI -> Machine Learning\'');
        expect(res2.isMultiStep).toBe(false);
        expect(res2.stepCount).toBe(1);
    });

    it('splits on && and -> delimiters', () => {
        const res = analyzeCommandInput('open chrome && search "latest AI news" -> summarize');
        expect(res.isMultiStep).toBe(true);
        expect(res.stepCount).toBe(3);
        expect(res.isParallel).toBe(false);
    });

    it('detects parallel markers', () => {
        const res = analyzeCommandInput('open chrome && open spotify in parallel');
        expect(res.isMultiStep).toBe(true);
        expect(res.isParallel).toBe(true);
    });

    it('splits on natural language sequential connectors (English and Hinglish)', () => {
        const resEng = analyzeCommandInput('fetch current weather then send email to team');
        expect(resEng.isMultiStep).toBe(true);
        expect(resEng.stepCount).toBe(2);

        const resHing = analyzeCommandInput('open notepad aur phir write daily summary');
        expect(resHing.isMultiStep).toBe(true);
        expect(resHing.stepCount).toBe(2);
    });

    it('splits numbered lists', () => {
        const res = analyzeCommandInput('1. open terminal\n2. run git status\n3. check branch');
        expect(res.isMultiStep).toBe(true);
        expect(res.stepCount).toBe(3);
    });
});
