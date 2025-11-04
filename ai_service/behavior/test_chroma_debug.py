from data_access import get_user_interactions
from bson import ObjectId

user_id = ObjectId("6868164751471f57737434d5")  # hoặc user_id thực tế
history = get_user_interactions(user_id)
print("User history:", history)
