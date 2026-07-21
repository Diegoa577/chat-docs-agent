/**
 * Type augmentation for the manual `next/navigation` mock
 * (`__mocks__/next/navigation.ts`).
 *
 * Jest resolves `next/navigation` to the manual mock at runtime (applied
 * globally in jest.setup.ts), but TypeScript type-checks against the real
 * module. This augmentation exposes the mock-only helpers (mockPush,
 * mockReplace, ...) so test files can import them from "next/navigation"
 * without type errors.
 */
import "next/navigation";

declare module "next/navigation" {
  export const mockPush: jest.Mock;
  export const mockReplace: jest.Mock;
  export const mockBack: jest.Mock;
  export const mockRefresh: jest.Mock;
  export const mockPrefetch: jest.Mock;
}
