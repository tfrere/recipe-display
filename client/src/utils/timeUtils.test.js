import { describe, it, expect } from "vitest";
import {
  parseTimeToMinutes,
  roundToNearestFive,
  formatTimeCompact,
  formatTime,
} from "./timeUtils";

describe("parseTimeToMinutes", () => {
  // ISO 8601
  describe("ISO 8601 durations", () => {
    it("should parse PT30M to 30 minutes", () => {
      expect(parseTimeToMinutes("PT30M")).toBe(30);
    });

    it("should parse PT1H to 60 minutes", () => {
      expect(parseTimeToMinutes("PT1H")).toBe(60);
    });

    it("should parse PT1H30M to 90 minutes", () => {
      expect(parseTimeToMinutes("PT1H30M")).toBe(90);
    });

    it("should parse PT45S to 0.75 minutes", () => {
      expect(parseTimeToMinutes("PT45S")).toBe(0.75);
    });

    it("should parse PT2H15M30S correctly", () => {
      expect(parseTimeToMinutes("PT2H15M30S")).toBe(135.5);
    });

    it("should be case insensitive for ISO 8601", () => {
      expect(parseTimeToMinutes("pt1h30m")).toBe(90);
    });

    it("should handle PT5M", () => {
      expect(parseTimeToMinutes("PT5M")).toBe(5);
    });

    it("should handle PT0M (zero duration)", () => {
      expect(parseTimeToMinutes("PT0M")).toBe(0);
    });

    it("should handle PT24H", () => {
      expect(parseTimeToMinutes("PT24H")).toBe(1440);
    });
  });

  // Legacy duration formats
  describe("Legacy durations", () => {
    it("should parse '1h30min' to 90 minutes", () => {
      expect(parseTimeToMinutes("1h30min")).toBe(90);
    });

    it("should parse '5min' to 5 minutes", () => {
      expect(parseTimeToMinutes("5min")).toBe(5);
    });

    it("should parse '2h' to 120 minutes", () => {
      expect(parseTimeToMinutes("2h")).toBe(120);
    });

    it("should parse '30 sec' to 0.5 minutes", () => {
      expect(parseTimeToMinutes("30 sec")).toBe(0.5);
    });
  });

  // Edge cases
  describe("Edge cases", () => {
    it("should return 0 for null", () => {
      expect(parseTimeToMinutes(null)).toBe(0);
    });

    it("should return 0 for undefined", () => {
      expect(parseTimeToMinutes(undefined)).toBe(0);
    });

    it("should return 0 for empty string", () => {
      expect(parseTimeToMinutes("")).toBe(0);
    });

    it("should return number directly if number given", () => {
      expect(parseTimeToMinutes(42)).toBe(42);
    });

    it("should return 0 for non-string non-number", () => {
      expect(parseTimeToMinutes({})).toBe(0);
    });
  });
});

describe("roundToNearestFive", () => {
  it("should round 7 to 5", () => {
    expect(roundToNearestFive(7)).toBe(5);
  });

  it("should round 13 to 15", () => {
    expect(roundToNearestFive(13)).toBe(15);
  });

  it("should keep 10 as 10", () => {
    expect(roundToNearestFive(10)).toBe(10);
  });

  it("should return 0 for falsy input", () => {
    expect(roundToNearestFive(0)).toBe(0);
    expect(roundToNearestFive(null)).toBe(0);
  });
});

describe("formatTimeCompact", () => {
  it("should format 90 minutes as '1h 30m'", () => {
    expect(formatTimeCompact(90)).toBe("1h 30m");
  });

  it("should format 60 minutes as '1h'", () => {
    expect(formatTimeCompact(60)).toBe("1h");
  });

  it("should format 30 minutes as '30m'", () => {
    expect(formatTimeCompact(30)).toBe("30m");
  });

  it("should format 0 as '0m'", () => {
    expect(formatTimeCompact(0)).toBe("0m");
  });

  it("should format 1500 minutes (25h) with days", () => {
    const result = formatTimeCompact(1500);
    expect(result).toContain("1j");
  });
});

describe("formatTime", () => {
  it("should format 90 minutes as '1 hour 30 min'", () => {
    expect(formatTime(90)).toBe("1 hour 30 min");
  });

  it("should format 60 minutes as '1 hour'", () => {
    expect(formatTime(60)).toBe("1 hour");
  });

  it("should format 30 minutes as '30 min'", () => {
    expect(formatTime(30)).toBe("30 min");
  });

  it("should format 0 as '0 min'", () => {
    expect(formatTime(0)).toBe("0 min");
  });
});
