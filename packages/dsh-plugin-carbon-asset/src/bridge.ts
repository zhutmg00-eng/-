/**
 * DeepSeek Harness (dsh) 碳资产引擎双模通信适配桥
 * 
 * 通信策略：
 * 1. 优先尝试向 FastAPI 服务 (默认 http://127.0.0.1:8000) 发起异步 HTTP 请求；
 * 2. 若 API 服务未启动或通信超时，自动降级为启动 Python 子进程调用 scripts/cli_bridge.py。
 */

// @ts-ignore
import { spawn } from 'node:child_process'
// @ts-ignore
import * as path from 'node:path'
// @ts-ignore
import { fileURLToPath } from 'node:url'

declare const process: any

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export interface BridgeConfig {
  apiBaseUrl?: string
  preferHttp?: boolean
  pythonPath?: string
  projectRoot?: string
}

export class CarbonEngineBridge {
  private apiBaseUrl: string
  private preferHttp: boolean
  private pythonPath: string
  private projectRoot: string

  constructor(config: BridgeConfig = {}) {
    const env = (typeof process !== 'undefined' && process.env) ? process.env : {}
    this.apiBaseUrl = config.apiBaseUrl || env.CARBON_API_BASE_URL || 'http://127.0.0.1:8000'
    this.preferHttp = config.preferHttp !== false
    this.pythonPath = config.pythonPath || env.PYTHON_PATH || 'python'
    this.projectRoot = config.projectRoot || path.resolve(__dirname, '../../../')
  }

  /**
   * 统一执行入口（带自动降级回退机制）
   */
  async execute<T = any>(endpoint: string, command: string, payload: any): Promise<T> {
    if (this.preferHttp) {
      try {
        return await this.callHttp<T>(endpoint, payload)
      } catch (err: any) {
        // HTTP 连接失败（服务未启动），自动降级为本地 CLI 进程
        return await this.callCli<T>(command, payload)
      }
    } else {
      return await this.callCli<T>(command, payload)
    }
  }

  /**
   * HTTP 通信
   */
  private async callHttp<T>(endpoint: string, payload: any): Promise<T> {
    const url = `${this.apiBaseUrl.replace(/\/+$/, '')}${endpoint}`
    const isGet = !payload || Object.keys(payload).length === 0

    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 8000)

    try {
      const response = await fetch(url, {
        method: isGet ? 'GET' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: isGet ? undefined : JSON.stringify(payload),
        signal: controller.signal,
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      return await response.json() as T
    } finally {
      clearTimeout(timeout)
    }
  }

  /**
   * Python 子进程 CLI 降级调用
   */
  private async callCli<T>(command: string, payload: any): Promise<T> {
    const scriptPath = path.resolve(this.projectRoot, 'scripts', 'cli_bridge.py')
    const jsonInput = JSON.stringify(payload || {})
    const env = (typeof process !== 'undefined' && process.env) ? process.env : {}

    return new Promise((resolve, reject) => {
      const proc = spawn(this.pythonPath, [scriptPath, command, '--json', jsonInput], {
        cwd: this.projectRoot,
        env: { ...env, PYTHONIOENCODING: 'utf-8' },
      })

      let stdout = ''
      let stderr = ''

      proc.stdout.on('data', (data: any) => { stdout += data.toString('utf-8') })
      proc.stderr.on('data', (data: any) => { stderr += data.toString('utf-8') })

      proc.on('close', (code: any) => {
        if (code === 0) {
          try {
            resolve(JSON.parse(stdout) as T)
          } catch (e: any) {
            reject(new Error(`CLI 输出 JSON 解析失败: ${stdout}`))
          }
        } else {
          reject(new Error(`Python CLI 执行失败 (code ${code}): ${stderr || stdout}`))
        }
      })

      proc.on('error', (err: any) => {
        reject(new Error(`无法启动 Python 解释器 (${this.pythonPath}): ${err.message}`))
      })
    })
  }
}
