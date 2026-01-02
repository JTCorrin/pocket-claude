import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.ixianprotocol.nearorbit',
  appName: 'Near Orbit',
  webDir: 'build',
  android: {
    // Required for @capacitor-community/background-geolocation
    useLegacyBridge: true
  },
  plugins: {
    LocalNotifications: {
      smallIcon: 'ic_stat_icon_config_sample',
      iconColor: '#488AFF'
    }
  }
};

export default config;
