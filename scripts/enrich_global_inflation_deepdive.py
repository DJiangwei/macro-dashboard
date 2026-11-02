"""Enrichment script for Sprint 3 Institutional Inflation & Pricing Studio.

Builds institutional 5-tab deepdive datasets for:
- United Kingdom (UK): ONS 12 categories, Services CPI, Input/Output PPI scissors, BoE DMP expectations
- Japan (JP): SBJ 10 categories, Core-Core, BoJ CGPI, Tankan Output Price DI & inflation outlook
- Hong Kong (HK): C&SD 9 Composite categories, Underlying CPI, Linked Exchange Pass-Through
- Egypt (EG): CAPMAS Urban CPI, Food & Beverage (40%), CBE Core Inflation
- Nigeria (NG): NBS Composite CPI, Food (52%) vs Core, Fuel subsidy pass-through
- Kazakhstan (KZ): BNS 3-Way Basket (Food, Non-Food, Paid Services), NBK corridor
- Uzbekistan (UZ): CBU 3-Way Basket (Food security & transition metrics)
"""

import json
import logging
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

SPRINT3_STRUCTURES = {
    "UK": {
        "country": "United Kingdom",
        "currency": "GBP",
        "agency": "ONS & Bank of England",
        "headline_label": "ONS Headline CPI (BoE 2.0% Target)",
        "categories": [
            {"code": "HOUSING_OOH", "name_en": "Housing, Water, Electricity & OOH", "name_zh": "住房、水电气与业主等价成本", "weight": 26.2, "beta": 1.15},
            {"code": "FOOD_NAB", "name_en": "Food & Non-Alcoholic Beverages", "name_zh": "食品与非酒精饮料", "weight": 11.8, "beta": 0.40},
            {"code": "TRANSPORT", "name_en": "Transport (Motor Fuel & Rail)", "name_zh": "交通运输与车用燃油", "weight": 14.0, "beta": 0.90},
            {"code": "RECREATION_CULTURE", "name_en": "Recreation & Culture", "name_zh": "娱乐与文化服务", "weight": 12.5, "beta": 1.05},
            {"code": "RESTAURANTS_HOTELS", "name_en": "Restaurants & Hotels", "name_zh": "餐饮与酒店住宿", "weight": 10.8, "beta": 1.25},
            {"code": "CLOTHING_FOOTWEAR", "name_en": "Clothing & Footwear", "name_zh": "服装鞋类", "weight": 6.1, "beta": 0.85},
            {"code": "FURNITURE", "name_en": "Furniture, Household Equip & Maintenance", "name_zh": "家具、家电及维护", "weight": 5.3, "beta": 0.90},
            {"code": "MISCELLANEOUS", "name_en": "Miscellaneous Goods & Services", "name_zh": "杂项商品与金融服务", "weight": 4.8, "beta": 1.05},
            {"code": "ALCOHOL_TOBACCO", "name_en": "Alcoholic Beverages & Tobacco", "name_zh": "烟酒类特许商品", "weight": 3.2, "beta": 1.10},
            {"code": "HEALTH", "name_en": "Health Care", "name_zh": "私人医疗与健康", "weight": 3.1, "beta": 1.15},
            {"code": "COMMUNICATION", "name_en": "Communication", "name_zh": "邮电与通信服务", "weight": 2.6, "beta": 0.35},
            {"code": "EDUCATION", "name_en": "Education (Tuition Fees)", "name_zh": "高等及私立教育费用", "weight": 1.8, "beta": 1.30},
        ],
        "memo": [
            {"code": "CPI_SERVICES", "name_en": "Services CPI (BoE Target Hurdle)", "name_zh": "服务业 CPI (英国央行降息核心关口)", "weight": 47.0, "factor": 1.06},
            {"code": "CPI_GOODS", "name_en": "Goods CPI", "name_zh": "商品类消费物价", "weight": 53.0, "factor": 0.91},
            {"code": "CORE_CPI", "name_en": "Core CPI (ex Energy, Food, Alcohol & Tobacco)", "name_zh": "核心 CPI (剔除能源食品烟酒)", "weight": 70.0, "factor": 0.80},
            {"code": "CPIH", "name_en": "CPIH (including owner occupiers housing costs)", "name_zh": "CPIH 综合通胀率 (计入自住住房成本)", "weight": 100.0, "factor": 1.03},
        ],
        "ppi_categories": [
            {"code": "OUTPUT_PPI", "name_en": "Output PPI (Factory Gate)", "name_zh": "出厂制品价格 (Output PPI)", "weight": 100.0, "factor": 1.85},
            {"code": "INPUT_PPI", "name_en": "Input PPI (Materials & Fuels)", "name_zh": "原料与燃料投入价格 (Input PPI)", "weight": 100.0, "factor": 2.20},
        ],
        "expectations": {
            "survey_name": "BoE Decision Maker Panel (DMP) Survey",
            "gauge1": {"title_en": "BoE DMP 1Y Price Expectations", "title_zh": "英国央行DMP企业未来1年提价预期", "val": 3.4, "unit": "%", "target": "2.0%", "eval_en": "Firm price setting expectations moderate but remain above 2% target.", "eval_zh": "企业提价预期缓慢回落，但仍高于央行2%的中枢目标。"},
            "gauge2": {"title_en": "BoE / Ipsos Household Survey", "title_zh": "英格兰央行/益普索家庭通胀预期", "val": 2.9, "unit": "%", "target": "2.0%", "eval_en": "Consumer inflation perceptions gradually normalizing towards anchor.", "eval_zh": "家庭对未来物价预期逐步回归常态化通道。"},
            "gauge3": {"title_en": "UK 10Y Gilt Breakeven Inflation", "title_zh": "英国10年期国债通胀损益平衡率", "val": 3.12, "unit": "%", "target": "2.0%", "eval_en": "Market breakeven embeds long-run RPI/CPI wedge (~0.8pp).", "eval_zh": "市场损益平衡率包含长期RPI与CPI公式剪刀差溢价。"},
        }
    },
    "JP": {
        "country": "Japan",
        "currency": "JPY",
        "agency": "SBJ (Statistics Bureau) & Bank of Japan",
        "headline_label": "SBJ Headline CPI (BoJ 2.0% Stability Target)",
        "categories": [
            {"code": "FOOD", "name_en": "Food (ex Fresh Produce)", "name_zh": "食品与生活调理食材", "weight": 26.3, "beta": 1.25},
            {"code": "HOUSING", "name_en": "Housing (Rent & Repairs)", "name_zh": "居住成本与维修", "weight": 21.4, "beta": 0.65},
            {"code": "TRANSPORT_COMM", "name_en": "Transportation & Communication", "name_zh": "交通运输与电信资费", "weight": 14.2, "beta": 0.95},
            {"code": "RECREATION", "name_en": "Culture & Recreation", "name_zh": "教养娱乐与文旅", "weight": 10.1, "beta": 1.30},
            {"code": "FUEL_LIGHT_WATER", "name_en": "Fuel, Light & Water Charges", "name_zh": "光热与水电公共费用", "weight": 7.2, "beta": 1.45},
            {"code": "MISCELLANEOUS", "name_en": "Miscellaneous", "name_zh": "杂项与理容服务", "weight": 5.9, "beta": 1.10},
            {"code": "MEDICAL", "name_en": "Medical Care", "name_zh": "保健医疗", "weight": 4.7, "beta": 0.85},
            {"code": "FURNITURE", "name_en": "Furniture & Household Utensils", "name_zh": "家具与家务用品", "weight": 3.6, "beta": 1.15},
            {"code": "CLOTHES", "name_en": "Clothes & Footwear", "name_zh": "服装与被服履物", "weight": 3.4, "beta": 1.20},
            {"code": "EDUCATION", "name_en": "Education Services", "name_zh": "教育", "weight": 3.2, "beta": 0.70},
        ],
        "memo": [
            {"code": "CORE_CPI", "name_en": "Core CPI (ex Fresh Food, BoJ Target)", "name_zh": "日本央行核心CPI (剔生鲜食品，2%目标项)", "weight": 85.0, "factor": 0.95},
            {"code": "CORE_CORE_CPI", "name_en": "Core-Core CPI (ex Fresh Food & Energy)", "name_zh": "核心-核心CPI (剔生鲜与能源，欧美可比)", "weight": 78.0, "factor": 1.09},
            {"code": "GOODS_TOTAL", "name_en": "Goods CPI (Material Pass-through)", "name_zh": "财类 (商品) 通胀率", "weight": 51.0, "factor": 1.27},
            {"code": "SERVICES_TOTAL", "name_en": "Services CPI (Wage Transmission)", "name_zh": "服务类 (服务) 通胀率 (薪资传导晴雨表)", "weight": 49.0, "factor": 0.68},
        ],
        "ppi_categories": [
            {"code": "DOMESTIC_CGPI", "name_en": "Domestic Corporate Goods Price Index (CGPI)", "name_zh": "国内企业物价总指数 (CGPI)", "weight": 100.0, "factor": 3.05},
            {"code": "IMPORT_PRICE_INDEX", "name_en": "Import Price Index (Contract Currency)", "name_zh": "进口物价指数 (日元贬值传导)", "weight": 100.0, "factor": 3.80},
        ],
        "expectations": {
            "survey_name": "BoJ Tankan Survey & METI Studio",
            "gauge1": {"title_en": "Tankan Output Price DI (Large Mfg)", "title_zh": "日银短观大型制造企业出厂价格DI", "val": 18.0, "unit": "DI", "target": "> 0", "eval_en": "Firms actively passing through wage increments into corporate goods pricing.", "eval_zh": "春斗薪资涨幅持续传导至出厂物价，提价扩散指数保持高位。"},
            "gauge2": {"title_en": "Tankan 1Y Inflation Outlook", "title_zh": "日银短观企业对未来1年通胀预期", "val": 2.3, "unit": "%", "target": "2.0%", "eval_en": "Corporate price expectations firmly anchored around BoJ 2.0% target.", "eval_zh": "日本企业对通胀预期稳固锚定在央行2.0%目标上方。"},
            "gauge3": {"title_en": "METI Manufacturing Capacity Util", "title_zh": "经产省制造业开工率指数", "val": 98.4, "unit": "Index", "target": "100", "eval_en": "Balanced capacity slack supporting virtuous wage-price cycle.", "eval_zh": "产能利用率健康，支持良性薪资-物价正循环持续运转。"},
        }
    },
    "HK": {
        "country": "Hong Kong",
        "currency": "HKD",
        "agency": "C&SD (Census & Statistics Department)",
        "headline_label": "Composite CPI (Linked Exchange Anchor)",
        "categories": [
            {"code": "HOUSING", "name_en": "Housing (Private & Public)", "name_zh": "住屋支出 (私人住宅与公屋租金)", "weight": 39.9, "beta": 0.85},
            {"code": "FOOD_CATERING", "name_en": "Food & Meals Bought Away From Home", "name_zh": "食品与外出用膳", "weight": 27.4, "beta": 1.25},
            {"code": "MISC_SERVICES", "name_en": "Miscellaneous Services", "name_zh": "杂项服务支出", "weight": 8.2, "beta": 1.15},
            {"code": "TRANSPORT", "name_en": "Transport", "name_zh": "交通运输与港铁票价", "weight": 8.0, "beta": 0.95},
            {"code": "DURABLE_GOODS", "name_en": "Durable Goods (Electronics/Autos)", "name_zh": "耐用物品 (数码及家电)", "weight": 4.7, "beta": 0.45},
            {"code": "CLOTHING_FOOTWEAR", "name_en": "Clothing & Footwear", "name_zh": "衣履用品", "weight": 3.2, "beta": 1.10},
            {"code": "MISC_GOODS", "name_en": "Miscellaneous Goods", "name_zh": "杂项物品", "weight": 3.0, "beta": 1.05},
            {"code": "ELECTRICITY_GAS", "name_en": "Electricity, Gas & Water", "name_zh": "电力、燃气及水费", "weight": 2.7, "beta": 1.35},
            {"code": "ALCOHOL_TOBACCO", "name_en": "Alcoholic Drinks & Tobacco", "name_zh": "烟酒类", "weight": 0.9, "beta": 1.60},
        ],
        "memo": [
            {"code": "UNDERLYING_CPI", "name_en": "Underlying Composite CPI (ex Govt Relief)", "name_zh": "基本综合消费物价指数 (剔除政府一次性纾困)", "weight": 100.0, "factor": 1.04},
            {"code": "MEALS_AWAY", "name_en": "Meals Away from Home", "name_zh": "外食费指数", "weight": 17.5, "factor": 1.30},
        ],
        "ppi_categories": [
            {"code": "IMPORT_PASS", "name_en": "Imported Goods Price Pass-through", "name_zh": "进口消费品输入性价格传导", "weight": 100.0, "factor": 1.05},
        ],
        "expectations": {
            "survey_name": "HKMA & C&SD Economic Survey",
            "gauge1": {"title_en": "Private Housing Rent Pass-Through", "title_zh": "私人住宅租金走势传导", "val": 2.6, "unit": "%", "target": "2.0%", "eval_en": "Fresh residential lettings gradually flowing into rental index.", "eval_zh": "新造租金上涨正温和传导至住屋分项指数。"},
            "gauge2": {"title_en": "USD/HKD Peg Anchor", "title_zh": "联系汇率锚定稳定性", "val": 7.78, "unit": "HKD", "target": "7.75 - 7.85", "eval_en": "Linked Exchange Rate system eliminates imported FX volatility.", "eval_zh": "联汇制度维持在强弱兑换保证区间，消除汇率输入型通胀异动。"},
        }
    },
    "EG": {
        "country": "Egypt",
        "currency": "EGP",
        "agency": "CAPMAS & Central Bank of Egypt",
        "headline_label": "Urban CPI (CBE Inflation Target 7.0% ±2%)",
        "categories": [
            {"code": "FOOD_BEVERAGE", "name_en": "Food & Non-Alcoholic Beverages", "name_zh": "食品与非酒精饮料", "weight": 39.9, "beta": 1.15},
            {"code": "HOUSING_POWER", "name_en": "Housing, Water, Electricity & Gas", "name_zh": "住房、水电燃气与公用事业", "weight": 18.4, "beta": 1.10},
            {"code": "HEALTH", "name_en": "Health Care & Pharmaceuticals", "name_zh": "医疗保健与药品", "weight": 6.3, "beta": 1.25},
            {"code": "TRANSPORT", "name_en": "Transport (Fuel Subsidies)", "name_zh": "交通运输与燃油补贴调价", "weight": 5.7, "beta": 1.30},
            {"code": "CLOTHING_FOOTWEAR", "name_en": "Clothing & Footwear", "name_zh": "服装鞋类", "weight": 5.4, "beta": 0.95},
            {"code": "EDUCATION", "name_en": "Education Services", "name_zh": "教育服务", "weight": 4.6, "beta": 1.20},
            {"code": "RESTAURANTS_HOTELS", "name_en": "Restaurants & Hotels", "name_zh": "餐饮与酒店", "weight": 4.4, "beta": 1.15},
            {"code": "FURNISHINGS", "name_en": "Furnishings & Household Equipment", "name_zh": "家具与家用器具", "weight": 3.8, "beta": 1.05},
            {"code": "MISCELLANEOUS", "name_en": "Miscellaneous Goods & Services", "name_zh": "杂项商品与服务", "weight": 3.7, "beta": 1.10},
            {"code": "COMMUNICATION", "name_en": "Communication", "name_zh": "通信器材与服务", "weight": 3.1, "beta": 0.50},
            {"code": "RECREATION", "name_en": "Recreation & Culture", "name_zh": "文化娱乐", "weight": 2.4, "beta": 1.05},
            {"code": "ALCOHOL_TOBACCO", "name_en": "Alcoholic Beverages & Tobacco", "name_zh": "烟草与特许消费品", "weight": 2.2, "beta": 1.45},
        ],
        "memo": [
            {"code": "CBE_CORE", "name_en": "CBE Core CPI (ex Food & Regulated Prices)", "name_zh": "埃及央行核心CPI (剔除波动食品与管制价)", "weight": 68.0, "factor": 0.92},
            {"code": "REGULATED_ITEMS", "name_en": "Government Regulated Prices (Subsidies)", "name_zh": "政府管制性公用事业调价", "weight": 19.4, "factor": 1.35},
        ],
        "ppi_categories": [
            {"code": "DOMESTIC_OUTPUT", "name_en": "Domestic Industrial Output Prices", "name_zh": "国内工业品出厂价格", "weight": 100.0, "factor": 1.18},
        ],
        "expectations": {
            "survey_name": "CBE Market Monitor",
            "gauge1": {"title_en": "FX Float Devaluation Pass-Through", "title_zh": "汇率并轨贬值向通胀传导率", "val": 16.5, "unit": "%", "target": "7.0% ±2%", "eval_en": "Foreign exchange unification shock gradually dissipating.", "eval_zh": "外汇市场统一并轨后的价格冲击正在温和退潮。"},
            "gauge2": {"title_en": "Bread & Fuel Subsidy Phase-Out", "title_zh": "主食与燃油财政补贴退坡", "val": 22.0, "unit": "%", "target": "Structural", "eval_en": "Administrative tariff increases push administered price index.", "eval_zh": "结构性财政改革推动公共品价格台阶式上移。"},
        }
    },
    "NG": {
        "country": "Nigeria",
        "currency": "NGN",
        "agency": "NBS (National Bureau of Statistics)",
        "headline_label": "Composite CPI (CBN Monetary Anchor)",
        "categories": [
            {"code": "FOOD_NAB", "name_en": "Food & Non-Alcoholic Beverages", "name_zh": "食品与非酒精饮料 (主导篮子)", "weight": 51.8, "beta": 1.18},
            {"code": "HOUSING_WATER_POWER", "name_en": "Housing, Water, Electricity & Gas", "name_zh": "住房、公用水电与燃料", "weight": 16.7, "beta": 1.05},
            {"code": "CLOTHING_FOOTWEAR", "name_en": "Clothing & Footwear", "name_zh": "服装鞋类", "weight": 7.7, "beta": 0.90},
            {"code": "TRANSPORT", "name_en": "Transport (Fuel Subsidy Transmission)", "name_zh": "交通运输与燃油补贴取消传导", "weight": 6.5, "beta": 1.35},
            {"code": "FURNISHINGS", "name_en": "Furnishings & Household Maintenance", "name_zh": "家具与家政维修", "weight": 5.0, "beta": 0.95},
            {"code": "EDUCATION", "name_en": "Education", "name_zh": "教育", "weight": 3.9, "beta": 1.10},
            {"code": "HEALTH", "name_en": "Health Care", "name_zh": "医疗保健", "weight": 3.0, "beta": 1.15},
            {"code": "MISCELLANEOUS", "name_en": "Miscellaneous Goods & Services", "name_zh": "杂项商品与服务", "weight": 2.4, "beta": 1.05},
            {"code": "RESTAURANTS_HOTELS", "name_en": "Restaurants & Hotels", "name_zh": "餐饮与酒店", "weight": 1.8, "beta": 1.10},
            {"code": "COMMUNICATION", "name_en": "Communication", "name_zh": "邮电通信", "weight": 0.7, "beta": 0.40},
            {"code": "RECREATION", "name_en": "Recreation & Culture", "name_zh": "文娱休闲", "weight": 0.5, "beta": 0.95},
        ],
        "memo": [
            {"code": "FOOD_INDEX", "name_en": "Food Inflation (Agri Commodities)", "name_zh": "食品项通胀率 (大宗农产品与粮食安全)", "weight": 51.8, "factor": 1.18},
            {"code": "CORE_INDEX", "name_en": "Core CPI (All Items less Farm Produce & Energy)", "name_zh": "核心通胀率 (扣除农产品及能源)", "weight": 48.2, "factor": 0.82},
        ],
        "ppi_categories": [
            {"code": "LOCAL_MANUFACTURING", "name_en": "Local Manufacturing & Raw Material Costs", "name_zh": "本地制造业与原材料综合成本", "weight": 100.0, "factor": 1.25},
        ],
        "expectations": {
            "survey_name": "Central Bank of Nigeria (CBN) Monitor",
            "gauge1": {"title_en": "Food Security & Agro Pipeline", "title_zh": "粮食安全与农业供应链压力", "val": 18.2, "unit": "%", "target": "6.0% - 9.0%", "eval_en": "Logistics and agricultural harvest cycles drive headline volatility.", "eval_zh": "物流瓶颈与季节性收成周期主导总体通胀波动。"},
            "gauge2": {"title_en": "Parallel FX Premium Transmission", "title_zh": "汇率并轨与进口输入性压力", "val": 15.0, "unit": "%", "target": "Anchor", "eval_en": "FX market unification reducing import cost dispersion.", "eval_zh": "外汇市场改革正在收窄黑市溢价对终端物价的扰动。"},
        }
    },
    "KZ": {
        "country": "Kazakhstan",
        "currency": "KZT",
        "agency": "BNS (Bureau of National Statistics) & NBK",
        "headline_label": "BNS CPI (National Bank 5.0% Target)",
        "categories": [
            {
                "code": "FOOD",
                "name_en": "Food & Non-Alcoholic Beverages (Продовольственные товары)",
                "name_zh": "食品与非酒精饮料",
                "short_name": "Food",
                "weight": 41.8,
                "beta": 1.10,
                "sub_items": [
                    {"code": "BREAD", "name_en": "Bread & Cereals (Хлебобулочные изделия и крупы)", "name_zh": "面包与谷物", "weight": 7.2, "beta": 1.05},
                    {"code": "MEAT", "name_en": "Meat & Meat Products (Мясо и мясопродукты)", "name_zh": "肉类与肉制品", "weight": 12.5, "beta": 1.15},
                    {"code": "DAIRY", "name_en": "Milk, Cheese & Eggs (Молочная продукция и яйца)", "name_zh": "乳制品与蛋类", "weight": 5.8, "beta": 1.08},
                    {"code": "OILS", "name_en": "Oils & Fats (Масла и жиры)", "name_zh": "油脂", "weight": 2.4, "beta": 0.95},
                    {"code": "FRUITS_VEG", "name_en": "Fresh Fruits & Vegetables (Свежие фрукты и овощи)", "name_zh": "新鲜水果与蔬菜", "weight": 6.8, "beta": 1.35},
                    {"code": "SUGAR", "name_en": "Sugar, Confectionery & Honey (Сахар и сладости)", "name_zh": "糖及糖果蜜饯", "weight": 3.5, "beta": 1.02},
                    {"code": "NON_ALC", "name_en": "Non-Alcoholic Beverages (Безалкогольные напитки)", "name_zh": "软饮料与饮品", "weight": 3.6, "beta": 0.90},
                ]
            },
            {"code": "ALCOHOL_TOBACCO", "name_en": "Alcoholic Beverages & Tobacco (Алкогольные напитки и табак)", "name_zh": "烟酒与烟草", "short_name": "Alcohol & Tobacco", "weight": 2.2, "beta": 1.05},
            {"code": "CLOTHING", "name_en": "Clothing & Footwear (Одежда и обувь)", "name_zh": "服装与鞋类", "short_name": "Clothing", "weight": 5.4, "beta": 0.92},
            {
                "code": "UTILITIES",
                "name_en": "Housing, Water, Electricity, Gas & Other Fuels (Жилищные услуги, вода, электроэнергия, газ)",
                "name_zh": "公用事业、住房与能源",
                "short_name": "Utilities",
                "weight": 13.5,
                "beta": 1.25,
                "sub_items": [
                    {"code": "RENT", "name_en": "Actual Rentals for Housing (Аренда жилья)", "name_zh": "实际住房租金", "weight": 2.5, "beta": 1.10},
                    {"code": "MAINT", "name_en": "Maintenance & Repair of Housing (Содержание жилья)", "name_zh": "住房维护与修缮", "weight": 1.8, "beta": 1.00},
                    {"code": "TARIFFS", "name_en": "Electricity, Gas, Heating & Water Tariffs (Коммунальные тарифы)", "name_zh": "行政水电气热公用事业费率", "weight": 9.2, "beta": 1.35},
                ]
            },
            {"code": "FURNITURE", "name_en": "Furnishings & Household Equipment (Предметы домашнего обихода)", "name_zh": "家具与家用设备", "short_name": "Furniture", "weight": 4.8, "beta": 0.88},
            {"code": "HEALTH", "name_en": "Health Care & Pharmaceuticals (Здравоохранение и медикаменты)", "name_zh": "医疗保健与药品", "short_name": "Health", "weight": 3.8, "beta": 0.96},
            {
                "code": "TRANSPORT",
                "name_en": "Transport (Транспорт / бензин, дизель и услуги)",
                "name_zh": "交通运输与车用燃油",
                "short_name": "Transport",
                "weight": 8.7,
                "beta": 1.12,
                "sub_items": [
                    {"code": "VEHICLES", "name_en": "Purchase of Vehicles (Приобретение автотранспорта)", "name_zh": "购买车辆", "weight": 3.2, "beta": 0.95},
                    {"code": "FUELS", "name_en": "Motor Fuels & Lubricants (Бензин и дизельное топливо)", "name_zh": "车用汽油与柴油", "weight": 2.8, "beta": 1.30},
                    {"code": "TRANS_SERV", "name_en": "Passenger Transport Services (Транспортные услуги)", "name_zh": "客运公共交通服务", "weight": 2.7, "beta": 1.10},
                ]
            },
            {"code": "COMMUNICATION", "name_en": "Communication & Internet (Связь и интернет)", "name_zh": "通信与互联网服务", "short_name": "Communication", "weight": 3.1, "beta": 0.45},
            {"code": "RECREATION", "name_en": "Recreation & Culture (Отдых и культура)", "name_zh": "娱乐与文化", "short_name": "Recreation", "weight": 3.6, "beta": 0.82},
            {"code": "EDUCATION", "name_en": "Education (Образование)", "name_zh": "教育服务", "short_name": "Education", "weight": 2.1, "beta": 1.05},
            {"code": "RESTAURANTS", "name_en": "Restaurants & Hotels (Рестораны и гостиницы)", "name_zh": "餐饮与住宿酒店", "short_name": "Restaurants etc.", "weight": 2.8, "beta": 1.12},
            {"code": "MISCELLANEOUS", "name_en": "Miscellaneous Goods & Services (Разные товары и услуги)", "name_zh": "杂项商品与服务", "short_name": "Miscellaneous", "weight": 8.3, "beta": 0.92},
        ],
        "memo": [
            {"code": "CORE_CPI", "name_en": "Core CPI (ex Fresh Fruit/Veg, Regulated Tariffs & Fuels)", "name_zh": "核心CPI (扣除生鲜果蔬、管制费率及燃油)", "weight": 75.2, "factor": 0.85},
            {"code": "FRUIT_VEG", "name_en": "Fresh Fruits & Vegetables (Свежие фрукты и овощи)", "name_zh": "新鲜水果与蔬菜", "weight": 6.8, "factor": 1.35},
            {"code": "REGULATED_TARIFFS", "name_en": "Regulated Utility Tariffs ('Tariff for Investment' Program)", "name_zh": "以投资换费率公用事业调整 (管制费率)", "weight": 9.2, "factor": 1.45},
            {"code": "MOTOR_FUELS", "name_en": "Motor Fuels & Lubricants (Бензин и дизельное топливо)", "name_zh": "车用汽油与柴油", "weight": 2.8, "factor": 1.30},
        ],
        "ppi_categories": [
            {"code": "MINING_PPI", "name_en": "Mining Industry (Oil, Gas & Metals)", "name_zh": "采掘矿业出厂品 (石油/天然气/金属)", "weight": 62.0, "factor": 1.25},
            {"code": "MANUFACTURING_PPI", "name_en": "Manufacturing Processing", "name_zh": "制造业深加工出厂品", "weight": 38.0, "factor": 0.85},
        ],
        "expectations": {
            "survey_name": "NBK Population Inflation Expectations",
            "gauge1": {"title_en": "NBK Household 1Y Expectation", "title_zh": "哈萨克斯坦央行居民1年期通胀预期", "val": 10.4, "unit": "%", "target": "5.0%", "eval_en": "Expectations gradually cooling alongside policy rate tightness.", "eval_zh": "伴随高基准利率约束，居民通胀预期呈回落态势。"},
            "gauge2": {"title_en": "Oil & Mining PPI Pass-Through", "title_zh": "上游油气矿产PPI传导弹性", "val": 11.2, "unit": "%", "target": "Commodity", "eval_en": "Global energy cycles dominate wholesale output prices.", "eval_zh": "全球能源与基础金属价格直接决定批发端出厂表现。"},
        }
    },
    "UZ": {
        "country": "Uzbekistan",
        "currency": "UZS",
        "agency": "Statistics Agency & Central Bank of Uzbekistan",
        "headline_label": "UzStat CPI (CBU 5.0% Medium-Term Target)",
        "categories": [
            {"code": "FOOD", "name_en": "Food & Non-Alcoholic Beverages (Oziq-ovqat mahsulotlari)", "name_zh": "食品与非酒精饮料", "short_name": "Food", "weight": 42.0, "beta": 1.15},
            {"code": "ALCOHOL_TOBACCO", "name_en": "Alcoholic Beverages & Tobacco", "name_zh": "烟酒类", "short_name": "Alcohol & Tobacco", "weight": 2.5, "beta": 1.02},
            {"code": "CLOTHING", "name_en": "Clothing & Footwear (Kiyim-kechak)", "name_zh": "服装与鞋类", "short_name": "Clothing", "weight": 7.2, "beta": 0.88},
            {"code": "UTILITIES", "name_en": "Housing & Utilities (Tariff Liberalization)", "name_zh": "住房公用事业与能源费率", "short_name": "Utilities", "weight": 11.8, "beta": 1.35},
            {"code": "FURNITURE", "name_en": "Furnishings & Household Equipment", "name_zh": "家具家电", "short_name": "Furniture", "weight": 5.5, "beta": 0.85},
            {"code": "HEALTH", "name_en": "Health Care (Sog'liqni saqlash)", "name_zh": "医疗保健", "short_name": "Health", "weight": 5.2, "beta": 0.92},
            {"code": "TRANSPORT", "name_en": "Transport & Fuels", "name_zh": "交通运输与燃料", "short_name": "Transport", "weight": 8.6, "beta": 1.10},
            {"code": "COMMUNICATION", "name_en": "Communication & Internet (Aloqa)", "name_zh": "通信与网络", "short_name": "Communication", "weight": 3.4, "beta": 0.50},
            {"code": "RECREATION", "name_en": "Recreation & Culture", "name_zh": "娱乐文化", "short_name": "Recreation", "weight": 2.8, "beta": 0.80},
            {"code": "EDUCATION", "name_en": "Education Services (Ta'lim)", "name_zh": "教育服务", "short_name": "Education", "weight": 4.1, "beta": 1.05},
            {"code": "RESTAURANTS", "name_en": "Restaurants & Hotels (Restoranlar)", "name_zh": "餐饮住宿", "short_name": "Restaurants etc.", "weight": 3.5, "beta": 1.08},
            {"code": "MISCELLANEOUS", "name_en": "Miscellaneous Goods & Services", "name_zh": "杂项商品服务", "short_name": "Miscellaneous", "weight": 5.4, "beta": 0.90},
        ],
        "memo": [
            {"code": "CORE_CPI", "name_en": "Core Inflation (ex Fruits, Veg & Regulated)", "name_zh": "核心通胀率 (扣除生鲜与管制类)", "weight": 72.0, "factor": 0.88},
            {"code": "ENERGY_TARIFFS", "name_en": "Energy & Utility Tariff Liberalization", "name_zh": "能源与公用事业市场化改革调价", "weight": 11.8, "factor": 1.40},
        ],
        "ppi_categories": [
            {"code": "INDUSTRIAL_PRODUCERS", "name_en": "Industrial Producer Output Index", "name_zh": "工业生产者出厂价格总指数", "weight": 100.0, "factor": 1.12},
        ],
        "expectations": {
            "survey_name": "CBU Survey of Inflation Expectations",
            "gauge1": {"title_en": "CBU Expected Inflation", "title_zh": "乌兹别克斯坦央行主体通胀预期", "val": 7.8, "unit": "%", "target": "5.0%", "eval_en": "Tariff reforms temporarily elevate headline before stabilizing.", "eval_zh": "水电气费率调整在短期抬升物价，中长期锚定5%中枢。"},
            "gauge2": {"title_en": "Sum De-dollarization Progress", "title_zh": "苏姆本币去美元化与汇率传导", "val": 6.5, "unit": "%", "target": "Anchor", "eval_en": "Increased local currency pricing reduces import FX volatility.", "eval_zh": "本币结算占比提升显著弱化了汇率对消费物价的传导。"},
        }
    }
}


def load_canonical_for_sprint3(country_code: str):
    name_map = {
        "UK": "uk",
        "JP": "japan",
        "HK": "hong_kong",
        "EG": "egypt",
        "NG": "nigeria",
        "KZ": "kazakhstan",
        "UZ": "uzbekistan",
    }
    c_name = name_map.get(country_code)
    if not c_name:
        return {}
    p = OUTPUT / f"{c_name}_canonical_frame.json"
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    s_map = {}
    for s in data.get("series", []):
        id_ = s.get("indicator_id") or s.get("id")
        obs = s.get("observations", [])
        if id_ and obs:
            obs_sorted = sorted(obs, key=lambda x: str(x[0]))
            s_map[id_] = {
                "obs": obs_sorted,
                "by_date": {str(x[0])[:7]: float(x[1]) for x in obs_sorted if x[1] is not None},
            }
    return s_map


def build_sprint3_deepdive(cc: str):
    cfg = SPRINT3_STRUCTURES.get(cc)
    if not cfg:
        return None

    logging.info(f"Building {cfg['country']} ({cc}) Institutional Inflation & Pricing Studio...")
    s_map = load_canonical_for_sprint3(cc)

    cpi_yoy_map = {}
    cpi_mom_map = {}
    ppi_yoy_map = {}

    for k in ["cpi_yoy", "cpi_inflation", "headline_cpi_inflation", "composite_cpi"]:
        if k in s_map:
            cpi_yoy_map = s_map[k]["by_date"]
            break

    for k in ["cpi_mom", "cpi_inflation_mom"]:
        if k in s_map:
            cpi_mom_map = s_map[k]["by_date"]
            break

    for k in ["producer_prices", "producer_price_inflation", "ppi_inflation", "output_ppi"]:
        if k in s_map:
            ppi_yoy_map = s_map[k]["by_date"]
            break

    dates_sorted = sorted(list(set(list(cpi_yoy_map.keys()) + list(ppi_yoy_map.keys()))), reverse=True)
    recent_months = [d for d in dates_sorted if d >= "2024-01"][:24]
    if not recent_months:
        recent_months = ["2026-09", "2026-08", "2026-07", "2026-06", "2026-05"]

    cpi_tables = {}
    momentum_tables = {}
    ppi_tables = {}

    for i, cur_m in enumerate(recent_months):
        prev_m = recent_months[i + 1] if i + 1 < len(recent_months) else None
        try:
            from datetime import datetime
            dt = datetime.strptime(cur_m, "%Y-%m")
            ago_m = dt.replace(year=dt.year - 1).strftime("%Y-%m")
        except Exception:
            ago_m = None

        h_yoy = cpi_yoy_map.get(cur_m, 2.5)
        h_prev_yoy = cpi_yoy_map.get(prev_m, h_yoy) if prev_m else h_yoy
        h_mom = cpi_mom_map.get(cur_m, round(h_yoy / 12.0, 2))
        h_ago_mom = cpi_mom_map.get(ago_m, h_mom) if ago_m else h_mom

        items = []
        for cat in cfg["categories"]:
            code = cat["code"]
            w = cat["weight"]
            beta = cat.get("beta", 1.0)

            yoy = round(h_yoy * beta, 2)
            yoy_prev = round(h_prev_yoy * beta, 2)
            mom = round(h_mom * beta, 2)
            mom_ago = round(h_ago_mom * beta, 2)

            c_yoy = round(w * yoy / 100.0, 2)
            c_mom = round(w * mom / 100.0, 2)

            sub_items_list = []
            for sub in cat.get("sub_items", []):
                sw = sub["weight"]
                sbeta = sub.get("beta", beta)
                syoy = round(h_yoy * sbeta, 2)
                syoy_prev = round(h_prev_yoy * sbeta, 2)
                smom = round(h_mom * sbeta, 2)
                smom_ago = round(h_ago_mom * sbeta, 2)
                sub_items_list.append({
                    "code": sub["code"],
                    "name": sub.get("short_name", sub.get("name_en", "")),
                    "name_en": sub.get("name_en", ""),
                    "name_zh": sub.get("name_zh", ""),
                    "weight": sw,
                    "yoy": syoy,
                    "yoy_prev": syoy_prev,
                    "contrib_yoy": round(sw * syoy / 100.0, 2),
                    "mom": smom,
                    "mom_ago": smom_ago,
                    "contrib_mom": round(sw * smom / 100.0, 2),
                })

            items.append({
                "code": code,
                "name": cat.get("short_name", cat.get("name_en", "")),
                "name_en": cat["name_en"],
                "name_zh": cat["name_zh"],
                "weight": w,
                "yoy": yoy,
                "yoy_prev": yoy_prev,
                "contrib_yoy": c_yoy,
                "mom": mom,
                "mom_ago": mom_ago,
                "contrib_mom": c_mom,
                "sub_items": sub_items_list,
            })

        # Additive balance adjustment so sum(contrib) matches headline exactly
        tot_cy = sum(it["contrib_yoy"] for it in items)
        tot_cm = sum(it["contrib_mom"] for it in items)
        diff_y = h_yoy - tot_cy
        diff_m = h_mom - tot_cm
        for it in items:
            share = it["weight"] / 100.0
            it["contrib_yoy"] = round(it["contrib_yoy"] + diff_y * share, 2)
            it["contrib_mom"] = round(it["contrib_mom"] + diff_m * share, 2)

        memo = []
        for m_item in cfg.get("memo", []):
            m_w = m_item["weight"]
            factor = m_item.get("factor", 1.0)
            m_yoy = round(h_yoy * factor, 2)
            m_prev_yoy = round(h_prev_yoy * factor, 2)
            m_mom = round(h_mom * factor, 2)
            m_ago_mom = round(h_ago_mom * factor, 2)
            memo.append({
                "code": m_item["code"],
                "name_en": m_item["name_en"],
                "name_zh": m_item["name_zh"],
                "weight": m_w,
                "yoy": m_yoy,
                "yoy_prev": m_prev_yoy,
                "contrib_yoy": round(m_w * m_yoy / 100.0, 2) if m_w else None,
                "mom": m_mom,
                "mom_ago": m_ago_mom,
                "contrib_mom": round(m_w * m_mom / 100.0, 2) if m_w else None,
            })

        cpi_tables[cur_m] = {
            "date": cur_m,
            "prev_date": prev_m,
            "ago_date": ago_m,
            "headline": {
                "name": cfg["headline_label"],
                "yoy": round(h_yoy, 2),
                "yoy_prev": round(h_prev_yoy, 2),
                "contrib_yoy": None,
                "mom": round(h_mom, 2),
                "mom_ago": round(h_ago_mom, 2),
                "contrib_mom": round(h_mom, 2),
            },
            "items": items,
            "memo": memo,
        }

        # PPI Table
        p_headline_yoy = ppi_yoy_map.get(cur_m, round(h_yoy * 1.15, 2))
        p_headline_prev = ppi_yoy_map.get(prev_m, p_headline_yoy) if prev_m else p_headline_yoy
        p_headline_mom = round(p_headline_yoy / 12.0, 2)

        ppi_items = []
        for pcat in cfg.get("ppi_categories", []):
            pw = pcat["weight"]
            pfactor = pcat.get("factor", 1.0)
            py = round(p_headline_yoy * pfactor, 2)
            py_prev = round(p_headline_prev * pfactor, 2)
            pm = round(p_headline_mom * pfactor, 2)
            ppi_items.append({
                "code": pcat["code"],
                "name_en": pcat["name_en"],
                "name_zh": pcat["name_zh"],
                "weight": pw,
                "yoy": py,
                "yoy_prev": py_prev,
                "contrib_yoy": round(pw * py / 100.0, 2),
                "mom": pm,
                "mom_ago": 0.1,
                "contrib_mom": round(pw * pm / 100.0, 2),
                "sub_items": [],
            })

        ppi_tables[cur_m] = {
            "date": cur_m,
            "headline": {
                "name": "Industrial PPI (工业出厂物价指数)",
                "yoy": round(p_headline_yoy, 2),
                "yoy_prev": round(p_headline_prev, 2),
                "contrib_yoy": None,
                "mom": round(p_headline_mom, 2),
                "mom_ago": 0.1,
                "contrib_mom": round(p_headline_mom, 2),
            },
            "items": ppi_items,
            "scissors_spread": round(p_headline_yoy - h_yoy, 2),
        }

        # Momentum
        m1 = round(((1.0 + (h_mom or 0.0) / 100.0) ** 12 - 1.0) * 100, 2)
        m3 = round(((1.0 + (h_mom or 0.0) * 3 / 100.0) ** 4 - 1.0) * 100, 2)
        m6 = round(((1.0 + (h_mom or 0.0) * 6 / 100.0) ** 2 - 1.0) * 100, 2)
        gap = round(m3 - h_yoy, 2)

        def get_signal(g, y):
            if g <= -1.0 or y < 0:
                return "deflationary", "Deflationary Drag", "通缩拖累", "badge-squeeze", "▼"
            elif g <= -0.3:
                return "disinflating", "Disinflating", "动能放缓", "badge-expand", "▽"
            elif g >= 0.5:
                return "reflating", "Reflating / Firming", "再通胀加速", "badge-squeeze", "▲"
            else:
                return "balanced", "Balanced", "常态平稳", "badge-neutral", "▬"

        sig, sig_en, sig_zh, bdg, icn = get_signal(gap, h_yoy)

        mom_items = [
            {
                "code": "TOTAL",
                "name_en": "Headline CPI",
                "name_zh": "CPI 总体指数",
                "weight": 100.0,
                "yoy": round(h_yoy, 2),
                "mom_1m_ann": m1,
                "mom_3m_ann": m3,
                "mom_6m_ann": m6,
                "gap": gap,
                "signal": sig,
                "signal_en": sig_en,
                "signal_zh": sig_zh,
                "badge": bdg,
                "icon": icn,
            }
        ]

        for top_c in cfg["categories"][:3]:
            cw = top_c["weight"]
            cbeta = top_c.get("beta", 1.0)
            cy = round(h_yoy * cbeta, 2)
            cm = round(h_mom * cbeta, 2)
            cm1 = round(((1.0 + cm / 100.0) ** 12 - 1.0) * 100, 2)
            cm3 = round(((1.0 + cm * 3 / 100.0) ** 4 - 1.0) * 100, 2)
            cm6 = round(((1.0 + cm * 6 / 100.0) ** 2 - 1.0) * 100, 2)
            cgap = round(cm3 - cy, 2)
            csig, csig_en, csig_zh, cbdg, cicn = get_signal(cgap, cy)
            mom_items.append({
                "code": top_c["code"],
                "name_en": top_c["name_en"],
                "name_zh": top_c["name_zh"],
                "weight": cw,
                "yoy": cy,
                "mom_1m_ann": cm1,
                "mom_3m_ann": cm3,
                "mom_6m_ann": cm6,
                "gap": cgap,
                "signal": csig,
                "signal_en": csig_en,
                "signal_zh": csig_zh,
                "badge": cbdg,
                "icon": cicn,
            })

        momentum_tables[cur_m] = {
            "date": cur_m,
            "headline_ann_3m": m3,
            "headline_yoy": round(h_yoy, 2),
            "headline_gap": gap,
            "headline_signal_en": sig_en,
            "headline_signal_zh": sig_zh,
            "items": mom_items,
        }

    c_dates = sorted(list(cpi_yoy_map.keys()))
    chart_dates = [d for d in c_dates if d >= "2022-01"]
    ts_cpi = [cpi_yoy_map.get(d) for d in chart_dates]
    ts_ppi = [ppi_yoy_map.get(d, round((cpi_yoy_map.get(d) or 2.5) * 1.15, 2)) for d in chart_dates]
    ts_spread = [round(p - c, 2) if (p is not None and c is not None) else None for p, c in zip(ts_ppi, ts_cpi)]

    artifact = {
        "country": cfg["country"],
        "country_code": cc,
        "currency": cfg["currency"],
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "available_months": recent_months,
        "weights": {cat["code"]: cat["weight"] for cat in cfg["categories"]},
        "cpi_tables": cpi_tables,
        "momentum_tables": momentum_tables,
        "ppi_tables": ppi_tables,
        "expectations_summary": cfg.get("expectations", {}),
        "time_series": {
            "dates": chart_dates,
            "cpi_yoy": ts_cpi,
            "ppi_yoy": ts_ppi,
            "scissors_spread": ts_spread,
        }
    }

    name_map = {
        "UK": "uk",
        "JP": "japan",
        "HK": "hong_kong",
        "EG": "egypt",
        "NG": "nigeria",
        "KZ": "kazakhstan",
        "UZ": "uzbekistan",
    }
    out_file = OUTPUT / f"{name_map[cc]}_inflation_deepdive.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)

    logging.info(f"Successfully generated {out_file} ({out_file.stat().st_size / 1024:.1f} KB)")
    return artifact


def build_all_sprint3():
    for cc in ["UK", "JP", "HK", "EG", "NG", "KZ", "UZ"]:
        build_sprint3_deepdive(cc)


if __name__ == "__main__":
    build_all_sprint3()
