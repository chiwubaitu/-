import json
import boto3

dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
# 假设课程表为`TeacherCourses`，结构包含`teacherId`、`courseId`、`courseName`
courses_table = dynamodb.Table('TeacherCourses')

def lambda_handler(event, context):
    try:
        # 测试阶段：返回固定课程列表（生产环境需从表中查询真实数据）
        courses = [
            {"courseId": "MATH101", "courseName": "高等数学"},
            {"courseId": "CS101", "courseName": "计算机基础"},
            {"courseId": "PHY101", "courseName": "大学物理"}
        ]
        
        # 生产环境：从DynamoDB查询教师的课程（需结合身份验证获取teacherId）
        # 示例：
        # teacher_id = event['requestContext']['authorizer']['teacherId']
        # response = courses_table.query(
        #     KeyConditionExpression='teacherId = :tid',
        #     ExpressionAttributeValues={':tid': teacher_id}
        # )
        # courses = response.get('Items', [])

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': 'https://dfg1elzq7v3yy.cloudfront.net',
                'Access-Control-Allow-Headers': 'Authorization, Content-Type'
            },
            'body': json.dumps(courses)  # 必须返回数组，确保前端可遍历
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': 'https://dfg1elzq7v3yy.cloudfront.net',
                'Access-Control-Allow-Headers': 'Authorization, Content-Type'
            },
            'body': json.dumps({'message': str(e)})
        }