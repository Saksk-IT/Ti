import type { ThemeStyle } from '../../../utils/theme';

export type DataCenterThemeTokens = {
  bg: string;
  surface: string;
  surface2: string;
  border: string;
  primary: string;
  cta: string;
  muted: string;
  text: string;
  fontBody: string;
  fontHeading: string;
};

export function getDataCenterThemeTokens(isDark: boolean, style: ThemeStyle): DataCenterThemeTokens;

export function buildDataCenterCompatPayload(ctx: any, activeTab: string): any;

export function buildDataCenterChartOption(
  id: string,
  payload: any,
  themeTokens: DataCenterThemeTokens,
  chart?: any,
): any;
