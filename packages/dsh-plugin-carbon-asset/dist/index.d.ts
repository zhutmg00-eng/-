/**
 * dsh-plugin-carbon-asset: DeepSeek Harness 官方规范生态插件
 *
 * 严格对齐 DeepSeek Harness (@deepseek-ai/dsh-tools) 规范与 Post-mortem 0001 规范：
 * 1. 采用命名空间导出 (name, inject, apply)，严禁使用 export default (避免 Loader 丢弃 inject 导致崩溃)；
 * 2. 所有工具 parameters 经由 defineTool 编译为合规 JSON Schema 对象 (type: "object", properties, required)；
 * 3. 严格声明 output.schema 与 output.render，杜绝模型系统提示词构建与对话流断流。
 */
export declare const name = "carbon-asset";
export declare const inject: string[];
export declare function apply(ctx: any, config?: any): void;
