import json
import boto3
# 导入Decimal类型用于判断
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
grades_table = dynamodb.Table('Grades')

def lambda_handler(event, context):
    try:
        response = grades_table.scan()
        items = response['Items']
        
        # 遍历所有成绩，转换Decimal类型为float
        for item in items:
            # 处理每个字段，若为Decimal则转为float
            for key, value in item.items():
                if isinstance(value, Decimal):
                    item[key] = float(value)  # 转换为float（或int(value)，根据需求）
        
        return {
            'statusCode': 200,
            'body': json.dumps(items)  # 此时可正常序列化
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'message': str(e)})
        }