/**
 * Manual Jest mock for `next/navigation`, applied globally via jest.setup.ts.
 *
 * Override per test, e.g.:
 *   import { usePathname, useParams } from "next/navigation";
 *   (usePathname as jest.Mock).mockReturnValue("/chat/abc");
 *   (useParams as jest.Mock).mockReturnValue({ conversationId: "abc" });
 */

export const mockPush = jest.fn();
export const mockReplace = jest.fn();
export const mockBack = jest.fn();
export const mockRefresh = jest.fn();
export const mockPrefetch = jest.fn();

// The real Next.js router is a stable object across renders. Returning a new
// object per call would break any memo/effect that depends on it (infinite
// render loop), so the mock must be stable too.
const stableRouter = {
  push: mockPush,
  replace: mockReplace,
  back: mockBack,
  refresh: mockRefresh,
  prefetch: mockPrefetch,
};

export const useRouter = jest.fn(() => stableRouter);

export const usePathname = jest.fn(() => "/");

export const useParams = jest.fn(() => ({}));

export const useSearchParams = jest.fn(() => new URLSearchParams());

export const useSelectedLayoutSegment = jest.fn(() => null);

export const redirect = jest.fn();

export const notFound = jest.fn();
