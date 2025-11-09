import json
import boto3
import csv
import base64
import re
from io import StringIO
import logging
from decimal import Decimal  # 导入Decimal模块

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
grades_table = dynamodb.Table('Grades')

CORS_HEADERS = {
    'Access-Control-Allow-Origin': 'https://dfg1elzq7v3yy.cloudfront.net',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
}

def parse_multipart_form_data(body, boundary):
    parts = re.split(boundary, body, flags=re.MULTILINE, maxsplit=10)
    file_content = None
    for i, part in enumerate(parts):
        if not part.strip():
            continue
        field_match = re.search(b'name="file"; filename="(.*?)"', part, re.IGNORECASE)
        if field_match:
            try:
                content_parts = part.split(b'\r\n\r\n', 1)
                if len(content_parts) < 2:
                    return None
                content = content_parts[1].rstrip(b'\r\n--')
                file_content = content.decode('utf-8')
                break
            except Exception as e:
                logger.error(f"解析文件内容失败: {str(e)}")
                return None
    return file_content

def lambda_handler(event, context):
    try:
        logger.info(f"收到请求事件: {json.dumps(event, indent=2)}")

        headers = event.get('headers', {})
        content_type = headers.get('content-type', headers.get('Content-Type', '')).lower()
        logger.info(f"请求Content-Type: [{content_type}]")

        boundary_match = re.search(r'boundary=(["\']?)(.*?)\1', content_type)
        if not boundary_match or 'multipart/form-data' not in content_type:
            logger.error(f"不支持的Content-Type: {content_type}")
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'message': '不支持的Content-Type，需为multipart/form-data'})
            }

        boundary = boundary_match.group(2).encode('utf-8')
        full_boundary = b'--' + boundary

        if event.get('isBase64Encoded', False):
            body = base64.b64decode(event['body'])
        else:
            body = event['body'].encode('utf-8')

        file_content = parse_multipart_form_data(body, full_boundary)
        if not file_content:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'message': '未找到文件内容'})
            }

        file_name = event.get('queryStringParameters', {}).get('filename', '')
        logger.info(f"文件名: {file_name}")
        if not file_name:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'message': '请传递文件名（filename参数）'})
            }

        if not file_name.endswith('.csv'):
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'message': '仅支持.csv格式文件'})
            }

        try:
            csv_reader = csv.DictReader(StringIO(file_content))
            logger.info(f"CSV表头: {csv_reader.fieldnames}")
        except Exception as e:
            logger.error(f"CSV解析失败: {str(e)}")
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'message': f'CSV格式错误: {str(e)}'})
            }

        # 校验CSV表头是否包含必要字段（course对应数据库字段）
        required_columns = ['studentId', 'course', 'term', 'score']
        missing_columns = [col for col in required_columns if col not in csv_reader.fieldnames]
        if missing_columns:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'message': f'CSV缺少必要列：{missing_columns}，表头必须包含{required_columns}'
                })
            }

        success_count = 0
        try:
            with grades_table.batch_writer() as batch:
                for row_num, row in enumerate(csv_reader, start=2):
                    # 提取CSV数据（统一用course_name变量存储课程名）
                    student_id = str(row['studentId']).strip()
                    course_name = str(row['course']).strip()  # 从CSV的course列提取
                    term = str(row['term']).strip()
                    score_str = str(row['score']).strip()

                    # 校验数据完整性（使用course_name变量）
                    if not (student_id and course_name and term):
                        return {
                            'statusCode': 400,
                            'headers': CORS_HEADERS,
                            'body': json.dumps({
                                'message': f'第{row_num}行数据不完整（学号/课程/学期不能为空）'
                            })
                        }

                    try:
                        # 分数转换为Decimal类型
                        score = Decimal(score_str)
                        if not (Decimal('0') <= score <= Decimal('100')):
                            raise ValueError
                    except ValueError:
                        return {
                            'statusCode': 400,
                            'headers': CORS_HEADERS,
                            'body': json.dumps({
                                'message': f'第{row_num}行分数错误（必须是0-100之间的数字）'
                            })
                        }

                    # 生成grade_id（使用course_name）
                    grade_id = f"{course_name}+{term}+{student_id}"
                    # 写入数据库（字段为course，值为course_name）
                    batch.put_item(Item={
                        'studentId': student_id,
                        'gradeId': grade_id,
                        'course': course_name,  # 对应数据库的course字段
                        'term': term,
                        'score': score
                    })
                    success_count += 1
            logger.info(f"批量写入成功，共{success_count}条数据")
        except Exception as e:
            logger.error(f"DynamoDB写入失败: {str(e)}")
            return {
                'statusCode': 500,
                'headers': CORS_HEADERS,
                'body': json.dumps({'message': f'数据写入失败: {str(e)}'})
            }

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'message': f'批量上传成功，共导入{success_count}条成绩'
            })
        }

    except Exception as e:
        logger.error(f"处理异常: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': f'处理失败：{str(e)}'})
        }