import boto3
import json

dynamodb = boto3.resource('dynamodb')
grades_table = dynamodb.Table('Grades')

def lambda_handler(event, context):
    try:
        # 从Cognito令牌中获取学生学号
        student_id = event['requestContext']['authorizer']['claims']['cognito:username']
        
        # 查询该学生的所有成绩
        response = grades_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('studentId').eq(student_id)
        )
        grades = response.get('Items', [])
        
        # 格式化返回数据
        result = []
        for grade in grades:
            result.append({
                'course': grade.get('course'),
                'semester': grade.get('term'),
                'score': float(grade.get('score'))  # 转换为float方便前端处理
            })
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': 'https://dfg1elzq7v3yy.cloudfront.net',  # 与前端域名一致
                'Content-Type': 'application/json'
            },
            'body': json.dumps(result)
        }
    
    except Exception as e:
        print(f"查询错误：{str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': 'https://dfg1elzq7v3yy.cloudfront.net',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'message': '查询成绩失败'})
        }