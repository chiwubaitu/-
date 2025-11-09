import json
import boto3
from datetime import datetime, timezone
import logging

# 配置日志（详细级别，便于调试）
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 初始化DynamoDB资源（确保区域和表名与实际一致）
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
period_table = dynamodb.Table('QueryPeriods')  # 时段表（主键：gradeId，字符串类型）

# CORS配置（严格匹配前端域名，避免跨域问题）
CORS_HEADERS = {
    'Access-Control-Allow-Origin': 'https://dfg1elzq7v3yy.cloudfront.net',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS'
}

def lambda_handler(event, context):
    try:
        # 安全获取HTTP方法（避免KeyError，兼容非代理集成场景）
        http_method = event.get('httpMethod', '').upper()  # 转为大写统一处理
        logger.info(f"收到请求：方法={http_method}，事件数据={event}")

        # 1. 处理OPTIONS预检请求（跨域必选）
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': CORS_HEADERS,
                'body': json.dumps({'message': '预检请求成功'})
            }

        # 2. 处理POST请求（设置/更新查询时段）
        if http_method == 'POST':
            # 解析请求体（容错：body为None时默认为空JSON）
            try:
                request_body = json.loads(event.get('body', '{}'))
                logger.info(f"POST请求体：{request_body}")
            except json.JSONDecodeError as e:
                return {
                    'statusCode': 400,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({
                        'message': f'请求体格式错误（需为JSON）：{str(e)}'
                    })
                }

            # 校验必填参数
            required_params = ['gradeID', 'startTime', 'endTime']
            missing_params = [p for p in required_params if p not in request_body]
            if missing_params:
                return {
                    'statusCode': 400,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({
                        'message': f'缺少必要参数：{missing_params}，请检查请求体'
                    })
                }

            # 提取并清洗参数
            grade_id = request_body['gradeID'].strip()
            start_time = request_body['startTime'].strip()
            end_time = request_body['endTime'].strip()

            # 校验gradeID非空
            if not grade_id:
                return {
                    'statusCode': 400,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({'message': 'gradeID不能为空'})
                }

            # 校验gradeID格式（课程ID_学期，如PHY101_2023年秋）
            if '_' not in grade_id:
                return {
                    'statusCode': 400,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({
                        'message': 'gradeID格式错误，应为"课程ID_学期"（如PHY101_2023年秋）'
                    })
                }

            # 校验时间格式（ISO 8601：YYYY-MM-DDTHH:MM，如2025-11-08T09:00）
            try:
                start_dt = datetime.fromisoformat(start_time).replace(tzinfo=timezone.utc)
                end_dt = datetime.fromisoformat(end_time).replace(tzinfo=timezone.utc)
                if start_dt >= end_dt:
                    return {
                        'statusCode': 400,
                        'headers': CORS_HEADERS,
                        'body': json.dumps({'message': '开始时间不能晚于结束时间'})
                    }
            except ValueError as e:
                return {
                    'statusCode': 400,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({
                        'message': f'时间格式错误（需为YYYY-MM-DDTHH:MM）：{str(e)}'
                    })
                }

            # 写入DynamoDB（用gradeId作为主键）
            try:
                period_table.put_item(Item={
                    'gradeId': grade_id,  # 与表主键定义一致
                    'startTime': start_time,
                    'endTime': end_time,
                    'updatedAt': datetime.now(timezone.utc).isoformat()  # UTC时间戳
                })
                logger.info(f"时段设置成功：gradeId={grade_id}，start={start_time}，end={end_time}")
                return {
                    'statusCode': 200,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({
                        'message': '查询时段设置成功',
                        'period': {
                            'gradeId': grade_id,
                            'startTime': start_time,
                            'endTime': end_time
                        }
                    })
                }
            except Exception as e:
                logger.error(f"DynamoDB写入失败：{str(e)}", exc_info=True)
                return {
                    'statusCode': 500,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({'message': f'数据库操作失败：{str(e)}'})
                }

        # 3. 处理GET请求（查询特定gradeId的时段）
        elif http_method == 'GET':
            # 安全获取查询参数（兼容queryStringParameters为None的情况）
            query_params = event.get('queryStringParameters', {}) or {}
            grade_id = query_params.get('gradeId', '').strip()

            if not grade_id:
                return {
                    'statusCode': 400,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({'message': '请在查询字符串中提供gradeId参数'})
                }

            # 从DynamoDB查询
            try:
                response = period_table.get_item(Key={'gradeId': grade_id})
                if 'Item' not in response:
                    logger.info(f"未找到时段：gradeId={grade_id}")
                    return {
                        'statusCode': 404,
                        'headers': CORS_HEADERS,
                        'body': json.dumps({
                            'message': f'未找到gradeId={grade_id}的时段设置'
                        })
                    }
                logger.info(f"查询到时段：gradeId={grade_id}，数据={response['Item']}")
                return {
                    'statusCode': 200,
                    'headers': CORS_HEADERS,
                    'body': json.dumps(response['Item'])  # 返回完整时段数据（含startTime/endTime）
                }
            except Exception as e:
                logger.error(f"DynamoDB查询失败：{str(e)}", exc_info=True)
                return {
                    'statusCode': 500,
                    'headers': CORS_HEADERS,
                    'body': json.dumps({'message': f'数据库操作失败：{str(e)}'})
                }

        # 4. 处理不支持的HTTP方法
        else:
            return {
                'statusCode': 405,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'message': f'不支持{http_method}方法，仅支持GET、POST、OPTIONS'
                })
            }

    except Exception as e:
        # 捕获所有未处理的异常（含详细堆栈）
        logger.error(f"服务器内部错误：{str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': '服务器处理失败，请稍后重试'})
        }