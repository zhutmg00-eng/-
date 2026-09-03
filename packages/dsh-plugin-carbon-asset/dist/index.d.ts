/**
 * dsh-plugin-carbon-asset: DeepSeek Harness 官方规范插件
 *
 * 为 DeepSeek Agent 赋予物流车队活动水平碳核算、模拟碳预算对标、
 * 新能源替换 TCO 投资回收期与边际减排成本 (MAC) 测算、多情景减排模拟及政策智能检索工具。
 */
export declare const name = "carbon-asset";
export declare const inject: string[];
export declare function apply(ctx: any, config?: any): void;
declare const _default: {
    name: string;
    inject: string[];
    apply: typeof apply;
};
export default _default;
