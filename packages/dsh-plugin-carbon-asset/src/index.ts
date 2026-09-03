/**
 * dsh-plugin-carbon-asset: DeepSeek Harness 官方规范插件
 * 
 * 为 DeepSeek Agent 赋予物流车队活动水平碳核算、模拟碳预算对标、
 * 新能源替换 TCO 投资回收期与边际减排成本 (MAC) 测算、多情景减排模拟及政策智能检索工具。
 */

import { CarbonEngineBridge } from './bridge.js'

export const name = 'carbon-asset'
export const inject = ['tools']

/**
 * 模拟或使用 @deepseek-ai/dsh-tools 的 defineTool 声明
 */
function defineTool(def: {
  name: string
  description: string
  parameters: Record<string, any>
  execute: (args: any) => Promise<any>
}) {
  return def
}

export function apply(ctx: any, config: any = {}) {
  const bridge = new CarbonEngineBridge(config)

  // 1. 车队碳排放基线测算工具
  ctx.tools?.register(
    defineTool({
      name: 'carbon_calculate',
      description: '测算物流企业车队的年度直接运营碳排放总量 (tCO2e)、模拟碳预算对标差额及碳价情景合规成本。',
      parameters: {
        company_name: { type: 'string', required: true, description: '企业或车队名称' },
        fleet: {
          type: 'array',
          required: true,
          description: '车队分组列表，每组包含 vehicle_type(车型), count(车辆数), annual_km(年均公里数), load_factor(满载率 0~1)',
        },
        scenario_reduction_target: {
          type: 'number',
          description: '模拟碳预算的情景减排紧缩目标，默认 0.10 (即90%历史强度基准)',
        },
      },
      async execute(args) {
        return await bridge.execute('/api/calculate', 'calculate', args)
      },
    })
  )

  // 2. TCO 全生命周期拥有成本与投资回收期测算工具
  ctx.tools?.register(
    defineTool({
      name: 'carbon_tco_evaluate',
      description: '测算燃油货车替换为纯电动商用车的全生命周期综合拥有成本(TCO)、初始增量投资(ΔCAPEX)、年运营节省(ΔOPEX)、静态投资回收期(年)以及单位吨碳减排边际成本(MAC)。',
      parameters: {
        vehicle_type: { type: 'string', required: true, description: '目标替换的燃油车型（如 重型柴油货车、中型柴油货车、轻型柴油货车、微型汽油货车）' },
        replace_count: { type: 'number', required: true, description: '拟替换为纯电车的车辆数量' },
        annual_km: { type: 'number', required: true, description: '单车年均运营里程 (km)' },
        annual_co2_reduction_t: { type: 'number', description: '该批车辆年碳减排量 (tCO2e)，若不提供可根据默认排放因子自动估算' },
        diesel_price_yuan_per_l: { type: 'number', description: '自定义柴油价格 (元/L，默认 7.50)' },
        electricity_price_yuan_per_kwh: { type: 'number', description: '自定义综合充电电价 (元/kWh，默认 0.80)' },
        ev_vehicle_price_wan: { type: 'number', description: '自定义新能源车单车购置价 (万元)' },
        lifespan_years: { type: 'number', description: '评估周期年限 (默认 5 年)' },
      },
      async execute(args) {
        return await bridge.execute('/api/tco/calculate', 'tco', args)
      },
    })
  )

  // 3. 车队减排情景模拟工具
  ctx.tools?.register(
    defineTool({
      name: 'carbon_reduction_scenario',
      description: '为车队组合配置减排措施（如将部分燃油车替换为纯电动车、提高调度满载率），评估减排潜力、对标成本节省及 TCO 投资回收期。',
      parameters: {
        baseline_fleet: { type: 'array', required: true, description: '基线车队配置列表' },
        changes: {
          type: 'object',
          required: true,
          description: '减排措施映射字典，如 {"替换为新能源物流车": 10, "提升满载率至0.85": 20}',
        },
        budget_reduction_target: { type: 'number', description: '基准预算缩减目标 (默认 0.10)' },
      },
      async execute(args) {
        return await bridge.execute('', 'reduction', args)
      },
    })
  )

  // 4. 碳市场政策法规智能问答工具
  ctx.tools?.register(
    defineTool({
      name: 'carbon_policy_query',
      description: '基于中国碳排放权交易法规、CCER自愿减排机制与绿色交通双碳政策知识库，回答企业的政策合规、基准线与履约问题，带政策条款原文来源溯源。',
      parameters: {
        question: { type: 'string', required: true, description: '用户或企业的政策咨询问题' },
        carbon_profile: { type: 'object', description: '可选的企业碳画像数据（如总排放量、车队规模、预算差额等）' },
      },
      async execute(args) {
        return await bridge.execute('/api/ask', 'policy', args)
      },
    })
  )

  // 5. 多企业/多车队碳资产横向对标工具
  ctx.tools?.register(
    defineTool({
      name: 'carbon_enterprise_compare',
      description: '对 2 个及以上物流企业或车队进行横向碳对标比较，输出各企业排放排名、模拟碳预算差额排名及情景成本对比。',
      parameters: {
        companies: {
          type: 'array',
          required: true,
          description: '企业列表，每个企业包含 company_name 和 fleet 列表',
        },
      },
      async execute(args) {
        return await bridge.execute('/api/compare', 'compare', args)
      },
    })
  )
}

export default {
  name,
  inject,
  apply,
}
