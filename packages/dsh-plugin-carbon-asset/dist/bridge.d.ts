/**
 * DeepSeek Harness (dsh) 碳资产引擎双模通信适配桥
 *
 * 通信策略：
 * 1. 优先尝试向 FastAPI 服务 (默认 http://127.0.0.1:8000) 发起异步 HTTP 请求；
 * 2. 若 API 服务未启动或通信超时，自动降级为启动 Python 子进程调用 scripts/cli_bridge.py。
 */
export interface BridgeConfig {
    apiBaseUrl?: string;
    preferHttp?: boolean;
    pythonPath?: string;
    projectRoot?: string;
}
export declare class CarbonEngineBridge {
    private apiBaseUrl;
    private preferHttp;
    private pythonPath;
    private projectRoot;
    constructor(config?: BridgeConfig);
    /**
     * 统一执行入口（带自动降级回退机制）
     */
    execute<T = any>(endpoint: string, command: string, payload: any): Promise<T>;
    /**
     * HTTP 通信
     */
    private callHttp;
    /**
     * Python 子进程 CLI 降级调用
     */
    private callCli;
}
