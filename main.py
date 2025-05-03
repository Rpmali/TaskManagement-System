from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
from google.auth.transport import requests
from google.cloud import firestore
import starlette.status as status
from datetime import datetime

app = FastAPI()

firestore_db = firestore.Client()

firebase_request_adapter = requests.Request()

app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory="templates")


def getUser(user_token):
    user = firestore_db.collection('user').document(user_token['user_id'])
    return user


def validateFirebaseToken(id_token):
    if not id_token:
        return None
    user_token = None
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(
            id_token, firebase_request_adapter)
    except ValueError as err:
        return None
    return user_token


def require_authentication(user_token):
    if not user_token:
        raise HTTPException(
            status_code=401, detail="You must be logged in to perform this action.")


@app.get('/')
async def root(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    return RedirectResponse(url='/dashboard', status_code=status.HTTP_302_FOUND)


@app.get('/login')
async def login(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return templates.TemplateResponse('login.html', {'request': request})

    return RedirectResponse(url='/dashboard', status_code=status.HTTP_302_FOUND)


@app.get('/dashboard')
async def dashboard(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

    try:
        print(f"Current user ID: {user_token['user_id']}")
        
        # Get all boards where user is a member
        all_boards = []
        
        # First, get all users
        users_ref = firestore_db.collection('user')
        
        # Try to get boards directly from the current user's collection first
        current_user_boards = users_ref.document(user_token['user_id']).collection('boards').stream()
        
        print("Checking current user's boards...")
        for board in current_user_boards:
            board_data = board.to_dict()
            print(f"Found board in current user's collection: {board.id}")
            print(f"Board data: {board_data}")
            all_boards.append({
                'id': board.id,
                'name': board_data.get('name'),
                'created_at': board_data.get('created_at'),
                'created_by': board_data.get('created_by'),
                'members': board_data.get('members', [])
            })
        
        print(f"Found {len(all_boards)} boards in current user's collection")
        
        # Then check other users' collections for boards where current user is a member
        all_users = users_ref.stream()
        for user in all_users:
            if user.id != user_token['user_id']:  # Skip current user as we already checked their boards
                print(f"Checking user: {user.id}")
                try:
                    # Get boards where current user is a member
                    boards = users_ref.document(user.id).collection('boards').where('members', 'array_contains', user_token['user_id']).stream()
                    
                    for board in boards:
                        print(f"Found board: {board.id}")
                        board_data = board.to_dict()
                        print(f"Board data: {board_data}")
                        
                        all_boards.append({
                            'id': board.id,
                            'name': board_data.get('name'),
                            'created_at': board_data.get('created_at'),
                            'created_by': board_data.get('created_by'),
                            'members': board_data.get('members', [])
                        })
                except Exception as e:
                    print(f"Error fetching boards for user {user.id}: {str(e)}")
                    continue

        print(f"Total boards found: {len(all_boards)}")
        print(f"Boards data: {all_boards}")

        # Calculate active and completed tasks
        active_tasks = 0
        completed_tasks = 0
        for board in all_boards:
            board_ref = firestore_db.collection('user').document(board['created_by']).collection('boards').document(board['id'])
            # Get active tasks
            active_tasks_query = board_ref.collection('tasks').where('status', '!=', 'done').get()
            active_tasks += len(active_tasks_query)
            # Get completed tasks
            completed_tasks_query = board_ref.collection('tasks').where('status', '==', 'done').get()
            completed_tasks += len(completed_tasks_query)

        # Get recent tasks for all boards
        recent_tasks = []
        for board in all_boards:
            board_ref = firestore_db.collection('user').document(board['created_by']).collection('boards').document(board['id'])
            board_tasks = board_ref.collection('tasks').order_by('created_at', direction=firestore.Query.DESCENDING).limit(5).get()
            for task in board_tasks:
                task_data = task.to_dict()
                task_data['id'] = task.id
                task_data['board_name'] = board['name']
                recent_tasks.append(task_data)
        
        # Sort recent tasks by creation date and take top 5
        recent_tasks.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        recent_tasks = recent_tasks[:5]

        return templates.TemplateResponse('dashboard.html', {
            'request': request,
            'user_token': user_token,
            'boards': all_boards,
            'active_tasks': active_tasks,
            'completed_tasks': completed_tasks,
            'recent_tasks': recent_tasks
        })
    except Exception as e:
        print(f"Error in dashboard route: {str(e)}")
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

@app.post('/create-user')
async def create_user(request: Request):
    try:
        data = await request.json()
        uid = data.get('uid')
        email = data.get('email')
        
        if not uid or not email:
            return JSONResponse(status_code=400, content={'error': 'Missing user data'})
        
        user_ref = firestore_db.collection('user').document(uid)
        user_ref.set({
            'email': email,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        user = user_ref.get()
        if not user.exists:
            return JSONResponse(status_code=500, content={'error': 'Failed to create user'})
            
        return JSONResponse(content={'status': 'success'})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.get('/add-board')
async def add_board(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse('add_board.html', {
        'request': request,
        'user_token': user_token
    })

@app.post('/add-board')
async def add_board(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

    require_authentication(user_token)

    data = await request.form()
    board_name = data.get('board_name')

    board_data = {
        'name': board_name,
        'created_at': firestore.SERVER_TIMESTAMP,
        'created_by': user_token['user_id'],
        'members': [user_token['user_id']]
    }

    board_ref = firestore_db.collection('user').document(user_token['user_id']).collection('boards').add(board_data)

    return RedirectResponse(url='/dashboard', status_code=status.HTTP_302_FOUND)

@app.get('/boards')
async def boards(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

    try:
        print(f"Current user ID: {user_token['user_id']}")
        
        # Get all boards where user is a member
        all_boards = []
        
        # First, get all users
        users_ref = firestore_db.collection('user')
        
        # Try to get boards directly from the current user's collection first
        current_user_boards = users_ref.document(user_token['user_id']).collection('boards').stream()
        
        print("Checking current user's boards...")
        for board in current_user_boards:
            board_data = board.to_dict()
            print(f"Found board in current user's collection: {board.id}")
            print(f"Board data: {board_data}")
            all_boards.append({
                'id': board.id,
                'name': board_data.get('name'),
                'created_at': board_data.get('created_at'),
                'created_by': board_data.get('created_by'),
                'members': board_data.get('members', [])
            })
        
        print(f"Found {len(all_boards)} boards in current user's collection")
        
        # Then check other users' collections for boards where current user is a member
        all_users = users_ref.stream()
        for user in all_users:
            if user.id != user_token['user_id']:  # Skip current user as we already checked their boards
                print(f"Checking user: {user.id}")
                try:
                    # Get boards where current user is a member
                    boards = users_ref.document(user.id).collection('boards').where('members', 'array_contains', user_token['user_id']).stream()
                    
                    for board in boards:
                        print(f"Found board: {board.id}")
                        board_data = board.to_dict()
                        print(f"Board data: {board_data}")
                        
                        all_boards.append({
                            'id': board.id,
                            'name': board_data.get('name'),
                            'created_at': board_data.get('created_at'),
                            'created_by': board_data.get('created_by'),
                            'members': board_data.get('members', [])
                        })
                except Exception as e:
                    print(f"Error fetching boards for user {user.id}: {str(e)}")
                    continue
        
        print(f"Total boards found: {len(all_boards)}")
        print(f"Boards data: {all_boards}")

        return templates.TemplateResponse('boards.html', {
            'request': request,
            'user_token': user_token,
            'boards': all_boards
        })
    except Exception as e:
        print(f"Error in boards route: {str(e)}")
        return RedirectResponse(url='/dashboard', status_code=status.HTTP_302_FOUND)

@app.get('/tasks/{board_id}')
async def tasks(request: Request, board_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

    try:
        print(f"Current user ID: {user_token['user_id']}")
        print(f"Looking for board: {board_id}")
        
        # Find the board in any user's collection where the current user is a member
        board_ref = None
        board_data = None
        creator_id = None
        
        # First check in current user's collection
        current_user_board = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id).get()
        if current_user_board.exists:
            print("Found board in current user's collection")
            board_data = current_user_board.to_dict()
            if user_token['user_id'] in board_data.get('members', []):
                print("Current user is a member of this board")
                board_ref = current_user_board.reference
                creator_id = board_data['created_by']
        
        # If not found in current user's collection, check other users
        if not board_ref:
            print("Checking other users' collections...")
            users_ref = firestore_db.collection('user')
            all_users = users_ref.stream()
            
            for user in all_users:
                if user.id != user_token['user_id']:
                    print(f"Checking user: {user.id}")
                    board_doc = users_ref.document(user.id).collection('boards').document(board_id).get()
                    if board_doc.exists:
                        temp_data = board_doc.to_dict()
                        print(f"Found board data: {temp_data}")
                        if user_token['user_id'] in temp_data.get('members', []):
                            print(f"User is a member of this board")
                            board_ref = board_doc.reference
                            board_data = temp_data
                            creator_id = temp_data['created_by']
                            break
        
        if not board_ref or not board_data:
            print("Board not found or user is not a member")
            return RedirectResponse(url='/boards', status_code=status.HTTP_302_FOUND)
        
        print(f"Board found. Creator ID: {creator_id}")
        print(f"Board data: {board_data}")
            
        # Get tasks based on user's role
        is_creator = creator_id == user_token['user_id']
        tasks_query = board_ref.collection('tasks')
        
        print(f"User is creator: {is_creator}")
        
        # If user is not the creator, only show unassigned tasks and tasks assigned to them
        if not is_creator:
            print("Getting tasks for regular member")
            tasks = []
            # Get tasks assigned to the user
            assigned_tasks = tasks_query.where('assignee', '==', user_token['user_id']).get()
            print(f"Found {len(assigned_tasks)} assigned tasks")
            tasks.extend(assigned_tasks)
            # Get unassigned tasks
            unassigned_tasks = tasks_query.where('assignee', '==', None).get()
            print(f"Found {len(unassigned_tasks)} unassigned tasks")
            tasks.extend(unassigned_tasks)
        else:
            print("Getting all tasks for creator")
            # Creator sees all tasks
            tasks = tasks_query.get()
            print(f"Found {len(tasks)} total tasks")
        
        task_list = []
        for task in tasks:
            task_data = task.to_dict()
            task_data['id'] = task.id
            
            # Convert Firestore Timestamp to datetime for completed_at
            if task_data.get('completed_at'):
                task_data['completed_at'] = task_data['completed_at'].strftime('%Y-%m-%d %H:%M') if hasattr(task_data['completed_at'], 'strftime') else task_data['completed_at']
            
            # Convert due_date string to datetime if it exists
            if task_data.get('due_date'):
                if isinstance(task_data['due_date'], str):
                    try:
                        task_data['due_date'] = datetime.strptime(task_data['due_date'], '%Y-%m-%d')
                    except ValueError:
                        task_data['due_date'] = None
                elif hasattr(task_data['due_date'], 'strftime'):
                    pass
                else:
                    task_data['due_date'] = None
            
            task_list.append(task_data)
        
        print(f"Final task list length: {len(task_list)}")
            
        # Get current board members
        members = []
        current_members = board_data.get('members', [])
        for member_id in current_members:
            user_ref = firestore_db.collection('user').document(member_id).get()
            if user_ref.exists:
                user_data = user_ref.to_dict()
                members.append({
                    'id': member_id,
                    'email': user_data.get('email'),
                    'display_name': user_data.get('display_name')
                })
        
        print(f"Found {len(members)} board members")
        
        # Get all users for member selection dropdown (only for creator)
        all_users = []
        if is_creator:
            all_users_query = firestore_db.collection('user').stream()
            for user in all_users_query:
                user_data = user.to_dict()
                if user_data and user.id not in current_members:  # Only include users who aren't already members
                    all_users.append({
                        'id': user.id,
                        'email': user_data.get('email'),
                        'display_name': user_data.get('display_name')
                    })
            print(f"Found {len(all_users)} available users to add")

        print("Rendering tasks template...")
        return templates.TemplateResponse('tasks.html', {
            'request': request,
            'user_token': user_token,
            'board_name': board_data.get('name'),
            'board_id': board_id,
            'tasks': task_list,
            'board_users': members,
            'available_users': all_users,
            'is_creator': is_creator,
            'board_data': board_data
        })
    except Exception as e:
        print(f"Error in tasks route: {str(e)}")
        print(f"Error details: ", e.__dict__)
        return RedirectResponse(url='/boards', status_code=status.HTTP_302_FOUND)

@app.post('/board/{board_id}/rename')
async def rename_board(request: Request, board_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return JSONResponse(status_code=401, content={'error': 'Unauthorized'})

    try:
        data = await request.json()
        new_name = data.get('name')
        
        if not new_name:
            return JSONResponse(status_code=400, content={'error': 'Name is required'})

        board_ref = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id)
        board = board_ref.get()
        
        if not board.exists:
            return JSONResponse(status_code=404, content={'error': 'Board not found'})
            
        board_data = board.to_dict()
        if board_data['created_by'] != user_token['user_id']:
            return JSONResponse(status_code=403, content={'error': 'Only board creator can rename the board'})

        members = board_data.get('members', [])
        for member_id in members:
            member_board_ref = firestore_db.collection('user').document(member_id).collection('boards').document(board_id)
            member_board_ref.update({'name': new_name})

        return JSONResponse(content={'status': 'success'})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.delete('/board/{board_id}/members/{user_id}')
async def remove_board_member(request: Request, board_id: str, user_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return JSONResponse(status_code=401, content={'error': 'Unauthorized'})

    try:
        board_ref = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id)
        board = board_ref.get()
        
        if not board.exists:
            return JSONResponse(status_code=404, content={'error': 'Board not found'})
            
        board_data = board.to_dict()
        if board_data['created_by'] != user_token['user_id']:
            return JSONResponse(status_code=403, content={'error': 'Only board creator can remove members'})

        members = board_data.get('members', [])
        if user_id in members:
            members.remove(user_id)
            board_data['members'] = members
            board_ref.set(board_data)

            member_board_ref = firestore_db.collection('user').document(user_id).collection('boards').document(board_id)
            member_board_ref.delete()

            tasks = board_ref.collection('tasks').where('assignee', '==', user_id).stream()
            for task in tasks:
                task.reference.update({
                    'assignee': None
                })

        return JSONResponse(content={'status': 'success'})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.delete('/tasks/{board_id}/{task_id}')
async def delete_task(request: Request, board_id: str, task_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return JSONResponse(status_code=401, content={'error': 'Unauthorized'})

    try:
        board_ref = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id)
        board = board_ref.get()
        
        if not board.exists:
            return JSONResponse(status_code=404, content={'error': 'Board not found'})
            
        board_data = board.to_dict()
        if user_token['user_id'] not in board_data.get('members', []):
            return JSONResponse(status_code=403, content={'error': 'Only board members can delete tasks'})

        task_ref = board_ref.collection('tasks').document(task_id)
        task_ref.delete()

        return JSONResponse(content={'status': 'success'})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.put('/tasks/{board_id}/{task_id}')
async def edit_task(request: Request, board_id: str, task_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return JSONResponse(status_code=401, content={'error': 'Unauthorized'})

    try:
        data = await request.json()
        title = data.get('title')
        description = data.get('description')
        due_date = data.get('due_date')
        assignee = data.get('assignee')
        
        if not title:
            return JSONResponse(status_code=400, content={'error': 'Title is required'})

        board_ref = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id)
        board = board_ref.get()
        
        if not board.exists:
            return JSONResponse(status_code=404, content={'error': 'Board not found'})
            
        board_data = board.to_dict()
        if user_token['user_id'] not in board_data.get('members', []):
            return JSONResponse(status_code=403, content={'error': 'Only board members can edit tasks'})

        task_data = {
            'title': title,
            'description': description,
            'due_date': due_date,
            'assignee': assignee
        }

        task_ref = board_ref.collection('tasks').document(task_id)
        task_ref.update(task_data)

        return JSONResponse(content={'status': 'success'})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.post('/add-task')
async def add_task(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

    try:
        data = await request.form()
        title = data.get('title')
        description = data.get('description')
        due_date = data.get('due_date')
        board_id = data.get('board_id')
        assignee = data.get('assignee')

        if not board_id:
            return RedirectResponse(url='/boards', status_code=status.HTTP_302_FOUND)

        # Find the board in any user's collection where the current user is a member
        board_ref = None
        board_data = None
        
        # First check in current user's collection
        current_user_board = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id).get()
        if current_user_board.exists:
            board_data = current_user_board.to_dict()
            if user_token['user_id'] in board_data.get('members', []):
                board_ref = current_user_board.reference
        
        # If not found in current user's collection, check other users
        if not board_ref:
            users_ref = firestore_db.collection('user')
            all_users = users_ref.stream()
            
            for user in all_users:
                if user.id != user_token['user_id']:
                    board_doc = users_ref.document(user.id).collection('boards').document(board_id).get()
                    if board_doc.exists:
                        temp_data = board_doc.to_dict()
                        if user_token['user_id'] in temp_data.get('members', []):
                            board_ref = board_doc.reference
                            board_data = temp_data
                            break

        if not board_ref or not board_data:
            return RedirectResponse(url='/boards', status_code=status.HTTP_302_FOUND)

        # Check for existing task with same title
        tasks_query = board_ref.collection('tasks').where('title', '==', title).get()
        if tasks_query:
            # Return to tasks page with error message
            return RedirectResponse(url=f'/tasks/{board_id}?error=Task with this title already exists', status_code=status.HTTP_302_FOUND)

        task_data = {
            'title': title,
            'description': description,
            'status': 'todo',
            'created_at': firestore.SERVER_TIMESTAMP,
            'assignee': assignee if assignee else None,
            'is_completed': False,
            'completed_at': None
        }

        if due_date:
            try:
                task_data['due_date'] = datetime.strptime(due_date, '%Y-%m-%d')
            except ValueError:
                task_data['due_date'] = None

        board_ref.collection('tasks').add(task_data)
        return RedirectResponse(url=f'/tasks/{board_id}', status_code=status.HTTP_302_FOUND)

    except Exception as e:
        print(f"Error in add_task route: {str(e)}")
        return RedirectResponse(url=f'/tasks/{board_id}', status_code=status.HTTP_302_FOUND)

@app.post('/board/{board_id}/members/{user_id}')
async def add_board_member(request: Request, board_id: str, user_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return JSONResponse(status_code=401, content={'error': 'Unauthorized'})

    try:
        # Find the board in creator's collection
        board_ref = None
        board_data = None
        
        # First check in current user's collection
        current_user_board = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id).get()
        if current_user_board.exists:
            board_data = current_user_board.to_dict()
            if board_data['created_by'] == user_token['user_id']:
                board_ref = current_user_board.reference

        if not board_ref or not board_data:
            return JSONResponse(status_code=403, content={'error': 'Only board creator can add members'})

        # Check if user exists
        new_member_ref = firestore_db.collection('user').document(user_id).get()
        if not new_member_ref.exists:
            return JSONResponse(status_code=404, content={'error': 'User not found'})

        # Check if user is already a member
        current_members = board_data.get('members', [])
        if user_id in current_members:
            return JSONResponse(status_code=400, content={'error': 'User is already a member'})

        # Add new member to the members list
        current_members.append(user_id)
        board_ref.update({
            'members': current_members
        })

        return JSONResponse(content={'status': 'success'})
        
    except Exception as e:
        print(f"Error in add_board_member: {str(e)}")
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.get('/task/{board_id}/{task_id}/edit')
async def get_task_for_edit(request: Request, board_id: str, task_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return JSONResponse(status_code=401, content={'error': 'Unauthorized'})

    try:
        # Find the board
        board_ref = None
        board_data = None
        
        # Check in current user's collection
        current_user_board = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id).get()
        if current_user_board.exists:
            board_data = current_user_board.to_dict()
            if user_token['user_id'] in board_data.get('members', []):
                board_ref = current_user_board.reference
        
        # If not found, check other users' collections
        if not board_ref:
            users_ref = firestore_db.collection('user')
            all_users = users_ref.stream()
            
            for user in all_users:
                if user.id != user_token['user_id']:
                    board_doc = users_ref.document(user.id).collection('boards').document(board_id).get()
                    if board_doc.exists:
                        temp_data = board_doc.to_dict()
                        if user_token['user_id'] in temp_data.get('members', []):
                            board_ref = board_doc.reference
                            board_data = temp_data
                            break

        if not board_ref:
            return JSONResponse(status_code=404, content={'error': 'Board not found'})

        # Get the task
        task_ref = board_ref.collection('tasks').document(task_id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            return JSONResponse(status_code=404, content={'error': 'Task not found'})

        task_data = task_doc.to_dict()
        task_data['id'] = task_id

        # Create a new dict with serializable values
        serializable_task = {
            'id': task_id,
            'title': task_data.get('title', ''),
            'description': task_data.get('description', ''),
            'assignee': task_data.get('assignee'),
            'status': task_data.get('status', 'todo'),
            'is_completed': task_data.get('is_completed', False)
        }
        
        # Handle datetime fields
        if task_data.get('due_date'):
            try:
                serializable_task['due_date'] = task_data['due_date'].strftime('%Y-%m-%d')
            except AttributeError:
                serializable_task['due_date'] = None
        
        if task_data.get('created_at'):
            try:
                serializable_task['created_at'] = task_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            except AttributeError:
                serializable_task['created_at'] = None
        
        if task_data.get('completed_at'):
            try:
                serializable_task['completed_at'] = task_data['completed_at'].strftime('%Y-%m-%d %H:%M:%S')
            except AttributeError:
                serializable_task['completed_at'] = None

        return JSONResponse(content={
            'task': serializable_task,
            'board_name': board_data.get('name')
        })

    except Exception as e:
        print(f"Error in get_task_for_edit: {str(e)}")
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.post('/task/{board_id}/{task_id}/edit')
async def edit_task(request: Request, board_id: str, task_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

    try:
        # Get form data
        form = await request.form()
        title = form.get('title')
        description = form.get('description')
        due_date = form.get('due_date')
        assignee = form.get('assignee')

        # Find the board
        board_ref = None
        board_data = None
        
        # Check in current user's collection
        current_user_board = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id).get()
        if current_user_board.exists:
            board_data = current_user_board.to_dict()
            if user_token['user_id'] in board_data.get('members', []):
                board_ref = current_user_board.reference
        
        # If not found, check other users' collections
        if not board_ref:
            users_ref = firestore_db.collection('user')
            all_users = users_ref.stream()
            
            for user in all_users:
                if user.id != user_token['user_id']:
                    board_doc = users_ref.document(user.id).collection('boards').document(board_id).get()
                    if board_doc.exists:
                        temp_data = board_doc.to_dict()
                        if user_token['user_id'] in temp_data.get('members', []):
                            board_ref = board_doc.reference
                            board_data = temp_data
                            break

        if not board_ref:
            return RedirectResponse(url='/boards', status_code=status.HTTP_302_FOUND)

        # Get the task
        task_ref = board_ref.collection('tasks').document(task_id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            return RedirectResponse(url=f'/tasks/{board_id}', status_code=status.HTTP_302_FOUND)

        task_data = task_doc.to_dict()
        
        # Only allow edit if user is board creator or task assignee
        if not (board_data['created_by'] == user_token['user_id'] or task_data.get('assignee') == user_token['user_id']):
            return RedirectResponse(url=f'/tasks/{board_id}', status_code=status.HTTP_302_FOUND)

        # Update task
        update_data = {
            'title': title,
            'description': description,
            'assignee': assignee if assignee else None
        }

        if due_date:
            try:
                update_data['due_date'] = datetime.strptime(due_date, '%Y-%m-%d')
            except ValueError:
                update_data['due_date'] = None

        task_ref.update(update_data)
        return RedirectResponse(url=f'/tasks/{board_id}', status_code=status.HTTP_302_FOUND)

    except Exception as e:
        print(f"Error in edit_task: {str(e)}")
        return RedirectResponse(url=f'/tasks/{board_id}', status_code=status.HTTP_302_FOUND)

@app.post('/task/{board_id}/{task_id}/complete')
async def complete_task(request: Request, board_id: str, task_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return JSONResponse(status_code=401, content={'error': 'Unauthorized'})

    try:
        # Find the board
        board_ref = None
        board_data = None
        
        # Check in current user's collection
        current_user_board = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id).get()
        if current_user_board.exists:
            board_data = current_user_board.to_dict()
            if user_token['user_id'] in board_data.get('members', []):
                board_ref = current_user_board.reference
        
        # If not found, check other users' collections
        if not board_ref:
            users_ref = firestore_db.collection('user')
            all_users = users_ref.stream()
            
            for user in all_users:
                if user.id != user_token['user_id']:
                    board_doc = users_ref.document(user.id).collection('boards').document(board_id).get()
                    if board_doc.exists:
                        temp_data = board_doc.to_dict()
                        if user_token['user_id'] in temp_data.get('members', []):
                            board_ref = board_doc.reference
                            board_data = temp_data
                            break

        if not board_ref:
            return JSONResponse(status_code=404, content={'error': 'Board not found'})

        # Get the task
        task_ref = board_ref.collection('tasks').document(task_id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            return JSONResponse(status_code=404, content={'error': 'Task not found'})

        task_data = task_doc.to_dict()
        
        # Only allow completion if user is board creator or task assignee
        if not (board_data['created_by'] == user_token['user_id'] or task_data.get('assignee') == user_token['user_id']):
            return JSONResponse(status_code=403, content={'error': 'Not authorized to complete this task'})

        # Toggle completion status
        current_status = task_data.get('is_completed', False)
        new_status = not current_status
        
        # Get current timestamp for completion
        now = datetime.now()
        
        update_data = {
            'is_completed': new_status,
            'completed_at': now if new_status else None,
            'status': 'done' if new_status else 'todo'
        }

        # Update the task
        task_ref.update(update_data)
        
        # Return the updated status and formatted completion time
        return JSONResponse(content={
            'status': 'success',
            'is_completed': new_status,
            'completed_at': now.strftime('%Y-%m-%d %H:%M') if new_status else None
        })

    except Exception as e:
        print(f"Error in complete_task: {str(e)}")
        return JSONResponse(status_code=500, content={'error': str(e)})

@app.get('/edit-task/{board_id}/{task_id}')
async def edit_task_page(request: Request, board_id: str, task_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

    try:
        # Find the board
        board_ref = None
        board_data = None
        
        # Check in current user's collection
        current_user_board = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id).get()
        if current_user_board.exists:
            board_data = current_user_board.to_dict()
            if user_token['user_id'] in board_data.get('members', []):
                board_ref = current_user_board.reference
        
        # If not found, check other users' collections
        if not board_ref:
            users_ref = firestore_db.collection('user')
            all_users = users_ref.stream()
            
            for user in all_users:
                if user.id != user_token['user_id']:
                    board_doc = users_ref.document(user.id).collection('boards').document(board_id).get()
                    if board_doc.exists:
                        temp_data = board_doc.to_dict()
                        if user_token['user_id'] in temp_data.get('members', []):
                            board_ref = board_doc.reference
                            board_data = temp_data
                            break

        if not board_ref:
            return RedirectResponse(url='/boards', status_code=status.HTTP_302_FOUND)

        # Get the task
        task_ref = board_ref.collection('tasks').document(task_id)
        task_doc = task_ref.get()
        
        if not task_doc.exists:
            return RedirectResponse(url=f'/tasks/{board_id}', status_code=status.HTTP_302_FOUND)

        task_data = task_doc.to_dict()
        task_data['id'] = task_id
        
        # Format datetime fields
        if task_data.get('due_date'):
            if hasattr(task_data['due_date'], 'strftime'):
                task_data['due_date'] = task_data['due_date'].strftime('%Y-%m-%d')
        
        # Get board members for assignee dropdown
        members = []
        for member_id in board_data.get('members', []):
            user_ref = firestore_db.collection('user').document(member_id).get()
            if user_ref.exists:
                user_data = user_ref.to_dict()
                members.append({
                    'id': member_id,
                    'email': user_data.get('email'),
                    'display_name': user_data.get('display_name')
                })

        return templates.TemplateResponse('tasks.html', {
            'request': request,
            'user_token': user_token,
            'board_id': board_id,
            'task': task_data,
            'board_users': members,
            'board_name': board_data.get('name'),
            'edit_mode': True,
            'show_task_form': True
        })

    except Exception as e:
        print(f"Error in edit_task_page: {str(e)}")
        return RedirectResponse(url=f'/tasks/{board_id}', status_code=status.HTTP_302_FOUND)

@app.get('/tasks')
async def get_all_tasks(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)

    try:
        all_tasks = []
        user_boards = []
        
        # First get all boards where user is a member
        users_ref = firestore_db.collection('user')
        all_users = users_ref.stream()
        
        for user in all_users:
            boards_ref = users_ref.document(user.id).collection('boards')
            boards = boards_ref.stream()
            
            for board in boards:
                board_data = board.to_dict()
                if user_token['user_id'] in board_data.get('members', []):
                    board_data['id'] = board.id
                    user_boards.append((board.reference, board_data))

        # Now get tasks from each board
        for board_ref, board_data in user_boards:
            tasks = board_ref.collection('tasks').stream()
            for task in tasks:
                task_data = task.to_dict()
                task_data['id'] = task.id
                task_data['board_id'] = board_data['id']
                task_data['board_name'] = board_data['name']
                
                # Only include tasks that are either assigned to the user or created by them
                if (task_data.get('assignee') == user_token['user_id'] or 
                    board_data['created_by'] == user_token['user_id']):
                    all_tasks.append(task_data)

        # Get all users for displaying assignee names
        all_users_data = []
        users = firestore_db.collection('user').stream()
        for user in users:
            user_data = user.to_dict()
            all_users_data.append({
                'id': user.id,
                'email': user_data.get('email'),
                'display_name': user_data.get('display_name')
            })

        return templates.TemplateResponse('all_tasks.html', {
            'request': request,
            'user_token': user_token,
            'tasks': all_tasks,
            'board_users': all_users_data
        })

    except Exception as e:
        print(f"Error in get_all_tasks: {str(e)}")
        return RedirectResponse(url='/dashboard', status_code=status.HTTP_302_FOUND)

@app.delete('/board/{board_id}')
async def delete_board(request: Request, board_id: str):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    
    if not user_token:
        return JSONResponse(status_code=401, content={'error': 'Unauthorized'})

    try:
        # Find the board in any user's collection where the current user is the creator
        board_ref = None
        board_data = None
        
        # First check in current user's collection
        current_user_board = firestore_db.collection('user').document(user_token['user_id']).collection('boards').document(board_id).get()
        if current_user_board.exists:
            board_data = current_user_board.to_dict()
            if board_data.get('created_by') == user_token['user_id']:
                board_ref = current_user_board.reference
        
        # If not found in current user's collection, check other users
        if not board_ref:
            users_ref = firestore_db.collection('user')
            all_users = users_ref.stream()
            
            for user in all_users:
                if user.id != user_token['user_id']:
                    board_doc = users_ref.document(user.id).collection('boards').document(board_id).get()
                    if board_doc.exists:
                        temp_data = board_doc.to_dict()
                        if temp_data.get('created_by') == user_token['user_id']:
                            board_ref = board_doc.reference
                            board_data = temp_data
                            break

        if not board_ref or not board_data:
            return JSONResponse(status_code=404, content={'error': 'Board not found'})

        # Only allow deletion if user is the creator
        if board_data.get('created_by') != user_token['user_id']:
            return JSONResponse(status_code=403, content={'error': 'Only board creator can delete the board'})

        # Check if there are any tasks in the board
        tasks = board_ref.collection('tasks').get()
        if tasks:
            return JSONResponse(status_code=400, content={'error': 'Cannot delete board: There are still tasks present'})

        # Check if there are any non-owning members
        members = board_data.get('members', [])
        if len(members) > 1:  # More than just the creator
            return JSONResponse(status_code=400, content={'error': 'Cannot delete board: There are still other members present'})

        # Delete the board from all members' collections
        for member_id in members:
            member_board_ref = firestore_db.collection('user').document(member_id).collection('boards').document(board_id)
            member_board_ref.delete()

        return JSONResponse(content={'status': 'success'})
        
    except Exception as e:
        print(f"Error in delete_board: {str(e)}")
        return JSONResponse(status_code=500, content={'error': str(e)})