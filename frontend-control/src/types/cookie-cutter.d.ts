declare module "cookie-cutter" {
  const cookie: {
    get(name: string): string | undefined;
    set(name: string, value: string, options?: Record<string, unknown>): void;
  };

  export default cookie;
}
