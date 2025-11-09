import boto3
import json
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
grades_table = dynamodb.Table('Grades')

def lambda_handler(event, context):
    try:
        # 解析前端数据
        data = json.loads(event['body'])
        student_id = data.get('studentId')
        course = data.get('courseName')
        score = data.get('score')
        term = data.get('semester')

        # 数据校验
        if not all([student_id, course, score, term]):
            return {
                'statusCode': 400,
                # 必须包含CORS头
                'headers': {
                    'Access-Control-Allow-Origin': 'https://dfg1ezlq7v3yy.cloudfront.net',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'message': '数据不完整'})
            }

        # 分数转换（Decimal类型）
        try:
            score_decimal = Decimal(str(float(score)))
            if score_decimal < 0 or score_decimal > 100:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Access-Control-Allow-Origin': 'https://dfg1ezlq7v3yy.cloudfront.net',
                        'Content-Type': 'application/json'
                    },
                    'body': json.dumps({'message': '分数必须在0-100之间'})
                }
        except ValueError:
            return {
                'statusCode': 400,
                'headers': {
                    'Access-Control-Allow-Origin': 'https://dfg1ezlq7v3yy.cloudfront.net',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({'message': '分数必须是有效数字'})
            }

        # 写入DynamoDB
        grade_id = f'{course}+{term}'
        grades_table.put_item(Item={
            'studentId': student_id,
            'gradeId': grade_id,
            'course': course,
            'score': score_decimal,
            'term': term
        })

        # 成功响应（含CORS头）
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': 'https://dfg1elzq7v3yy.cloudfront.net',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'message': '成绩录入成功'})
        }

    except Exception as e:
        print(f"错误：{str(e)}")
        # 异常响应（含CORS头）
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': 'https://dfg1ezlq7v3yy.cloudfront.net',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'message': '服务器错误'})
        }