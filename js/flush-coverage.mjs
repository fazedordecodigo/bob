import v8 from "node:v8";
import { afterAll } from "vitest";

afterAll(() => {
  if (typeof v8.takeCoverage === "function") {
    v8.takeCoverage();
  }
});
