/// <reference path="./types/index.d.ts" />

interface IAppOption {
  globalData: {
    userInfo?: WechatMiniprogram.UserInfo,
    isDarkMode: boolean,
    themeMode: 'light' | 'dark' | 'system',
    themeStyle: 'default' | 'mist' | 'dune' | 'pine' | 'celadon',
    fontStyle: 'system' | 'elegant' | 'modern' | 'rounded' | 'classic',
  }
  userInfoReadyCallback?: WechatMiniprogram.GetUserInfoSuccessCallback,
}