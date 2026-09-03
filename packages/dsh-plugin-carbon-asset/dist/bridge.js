/**
 * DeepSeek Harness (dsh) 碳资产引擎双模通信适配桥
 *
 * 通信策略：
 * 1. 优先尝试向 FastAPI 服务 (默认 http://127.0.0.1:8000) 发起异步 HTTP 请求；
 * 2. 若 API 服务未启动或通信超时，自动降级为启动 Python 子进程调用 scripts/cli_bridge.py。
 */
// @ts-ignore
import { spawn } from 'node:child_process';
// @ts-ignore
import * as path from 'node:path';
// @ts-ignore
import { fileURLToPath } from 'node:url';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
export class CarbonEngineBridge {
    apiBaseUrl;
    preferHttp;
    pythonPath;
    projectRoot;
    constructor(config = {}) {
        const env = (typeof process !== 'undefined' && process.env) ? process.env : {};
        this.apiBaseUrl = config.apiBaseUrl || env.CARBON_API_BASE_URL || 'http://127.0.0.1:8000';
        this.preferHttp = config.preferHttp !== false;
        this.pythonPath = config.pythonPath || env.PYTHON_PATH || 'python';
        this.projectRoot = config.projectRoot || path.resolve(__dirname, '../../../');
    }
    /**
     * 统一执行入口（带自动降级回退机制）
     */
    async execute(endpoint, command, payload) {
        if (this.preferHttp) {
            try {
                return await this.callHttp(endpoint, payload);
            }
            catch (err) {
                // HTTP 连接失败（服务未启动），自动降级为本地 CLI 进程
                return await this.callCli(command, payload);
            }
        }
        else {
            return await this.callCli(command, payload);
        }
    }
    /**
     * HTTP 通信
     */
    async callHttp(endpoint, payload) {
        const url = `${this.apiBaseUrl.replace(/\/+$/, '')}${endpoint}`;
        const isGet = !payload || Object.keys(payload).length === 0;
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 8000);
        try {
            const response = await fetch(url, {
                method: isGet ? 'GET' : 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: isGet ? undefined : JSON.stringify(payload),
                signal: controller.signal,
            });
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            return await response.json();
        }
        finally {
            clearTimeout(timeout);
        }
    }
    /**
     * Python 子进程 CLI 降级调用
     */
    async callCli(command, payload) {
        const scriptPath = path.resolve(this.projectRoot, 'scripts', 'cli_bridge.py');
        const jsonInput = JSON.stringify(payload || {});
        const env = (typeof process !== 'undefined' && process.env) ? process.env : {};
        return new Promise((resolve, reject) => {
            const proc = spawn(this.pythonPath, [scriptPath, command, '--json', jsonInput], {
                cwd: this.projectRoot,
                env: { ...env, PYTHONIOENCODING: 'utf-8' },
            });
            let stdout = '';
            let stderr = '';
            proc.stdout.on('data', (data) => { stdout += data.toString('utf-8'); });
            proc.stderr.on('data', (data) => { stderr += data.toString('utf-8'); });
            proc.on('close', (code) => {
                if (code === 0) {
                    try {
                        resolve(JSON.parse(stdout));
                    }
                    catch (e) {
                        reject(new Error(`CLI 输出 JSON 解析失败: ${stdout}`));
                    }
                }
                else {
                    reject(new Error(`Python CLI 执行失败 (code ${code}): ${stderr || stdout}`));
                }
            });
            proc.on('error', (err) => {
                reject(new Error(`无法启动 Python 解释器 (${this.pythonPath}): ${err.message}`));
            });
        });
    }
}
