import { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'ai.lipi.app',
  appName: 'LIPI',
  webDir: 'public',
  server: {
    url: 'http://192.168.1.66:3000',
    cleartext: true
  }
};

export default config;
