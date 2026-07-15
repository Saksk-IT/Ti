/**
 * wx-extensions.d.ts
 * 扩展微信小程序 API 类型声明，消除 (wx as any).xxx 用法
 */

declare namespace WechatMiniprogram {
  interface Wx {
    /** 获取设备基础信息 */
    getDeviceInfo(): {
      brand: string;
      model: string;
      system: string;
      platform: string;
      deviceOrientation: string;
    };

    /** 获取窗口信息 */
    getWindowInfo(): {
      pixelRatio: number;
      screenWidth: number;
      screenHeight: number;
      windowWidth: number;
      windowHeight: number;
      statusBarHeight: number;
      safeArea: {
        left: number;
        right: number;
        top: number;
        bottom: number;
        width: number;
        height: number;
      };
    };

    /** 获取 App 基础信息 */
    getAppBaseInfo(): {
      SDKVersion: string;
      enableDebug: boolean;
      host: { appId: string };
      language: string;
      version: string;
      theme?: 'light' | 'dark';
    };

    /** 获取系统设置 */
    getSystemSetting(): {
      bluetoothEnabled: boolean;
      locationEnabled: boolean;
      wifiEnabled: boolean;
      deviceOrientation: string;
    };

    /** 获取菜单按钮（右上角胶囊按钮）的布局位置信息 */
    getMenuButtonBoundingClientRect(): {
      width: number;
      height: number;
      top: number;
      right: number;
      bottom: number;
      left: number;
    };

    /** 拍摄或从相册选择图片/视频 */
    chooseMedia(options: {
      count?: number;
      mediaType?: Array<'image' | 'video' | 'mix'>;
      sourceType?: Array<'album' | 'camera'>;
      maxDuration?: number;
      sizeType?: Array<'original' | 'compressed'>;
      camera?: 'back' | 'front';
      success?: (res: {
        tempFiles: Array<{
          tempFilePath: string;
          size: number;
          duration?: number;
          height?: number;
          width?: number;
          thumbTempFilePath?: string;
          fileType?: string;
        }>;
        type: string;
      }) => void;
      fail?: (err: { errMsg: string }) => void;
      complete?: () => void;
    }): void;
  }
}
