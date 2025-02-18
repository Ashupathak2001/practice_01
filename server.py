import streamlit as st
import uuid
from graphql import (GraphQLObjectType, GraphQLString, GraphQLSchema, 
                     GraphQLField, GraphQLList, GraphQLArgument, execute)
from graphql.language import parse
from datetime import datetime, timedelta
import pytz
import plotly.express as px
import pandas as pd
from plyer import notification
import threading
import time

class NotificationManager:
    def __init__(self, todo_manager):
        self.todo_manager = todo_manager
        self.notification_thread = None
        self.stop_notifications = False

    def send_todo_notification(self, todos):
        """Send desktop notifications for due todos"""
        for todo in todos:
            notification.notify(
                title='Todo Due Soon!',
                message=f"Title: {todo['title']}\nDescription: {todo['description']}\nPriority: {todo['priority']}",
                app_icon=None,
                timeout=10  # seconds
            )

    def check_due_todos(self):
        """Check todos with pending reminders and send notifications."""
        current_time = datetime.now(pytz.UTC)
        due_reminders = []

        for todo in self.todo_manager.todos:
            if todo['reminder_datetime']:
                reminder_time = datetime.fromisoformat(todo['reminder_datetime'])
                # Trigger notification if it's time for the reminder
                if reminder_time <= current_time and not todo['completed']:
                    due_reminders.append(todo)

        if due_reminders:
            self.send_todo_notification(due_reminders)

    def start_notification_service(self, interval=300):  # Check every 5 minutes
        """Start background notification service"""
        def notification_loop():
            while not self.stop_notifications:
                self.check_due_todos()
                time.sleep(interval)

        self.notification_thread = threading.Thread(target=notification_loop, daemon=True)
        self.notification_thread.start()

    def stop_notification_service(self):
        """Stop the notification service"""
        self.stop_notifications = True
        if self.notification_thread:
            self.notification_thread.join()

class TodoManager:
    def __init__(self):
        self.todos = []
        self.categories = ['Personal', 'Education', 'Work', 'Shopping', 'Health', 'Other']
        

    def add_todo(self, title, description, priority, due_date, category, reminder_datetime=None):
        """Add a new todo with more detailed information"""
        todo = {
            'id': str(uuid.uuid4()),  # Use UUID for unique IDs
            'unique_id': str(uuid.uuid4()), # Use UUID for unique IDs
            'title': title,
            'description': description,
            'priority': priority,
            'due_date': due_date,
            'category': category,
            'created_at': datetime.now(pytz.UTC).isoformat(),
            'completed': False,
            'reminder_datetime': reminder_datetime
        }
        self.todos.append(todo)
        return todo

    def get_todos(self, filter_completed=None, sort_by=None, category=None):
        """Retrieve todos with optional filtering and sorting"""
        filtered_todos = self.todos
        
        if filter_completed is not None:
            filtered_todos = [todo for todo in filtered_todos if todo['completed'] == filter_completed]
        
        if category:
            filtered_todos = [todo for todo in filtered_todos if todo['category'].lower() == category.lower()]

        if sort_by == 'priority':
            filtered_todos.sort(key=lambda x: ['low', 'medium', 'high'].index(x['priority']))
        elif sort_by == 'due_date':
            filtered_todos.sort(key=lambda x: x['due_date'])
        
        return filtered_todos

    def update_todo_status(self, todo_id, completed):
        """Update the completion status of a todo"""
        for todo in self.todos:
            if todo['id'] == todo_id:
                todo['completed'] = completed
                return todo
        return None

    def delete_todo(self, todo_id):
        """Delete a todo by its ID"""
        self.todos = [todo for todo in self.todos if todo['id'] != todo_id]
        return "Deleted"

    def get_todos_data_for_visualization(self):
        """Prepare todos data for visualization"""
        completed = len([todo for todo in self.todos if todo['completed']])
        pending = len([todo for todo in self.todos if not todo['completed']])
        
        priority_data = {}
        for priority in ['low', 'medium', 'high']:
            priority_data[priority] = {
                'completed': len([todo for todo in self.todos if todo['completed'] and todo['priority'] == priority]),
                'pending': len([todo for todo in self.todos if not todo['completed'] and todo['priority'] == priority])
            }

        return {
            'status': [
                {'Status': 'Completed', 'Count': completed},
                {'Status': 'Pending', 'Count': pending}
            ],
            'priority': priority_data
        }

def get_graphql_schema(todo_manager):
    TodoType = GraphQLObjectType(
        name='Todo',
        fields={
            'id': GraphQLField(GraphQLString),
            'title': GraphQLField(GraphQLString),
            'description': GraphQLField(GraphQLString),
            'priority': GraphQLField(GraphQLString),
            'due_date': GraphQLField(GraphQLString),
            'created_at': GraphQLField(GraphQLString),
            'completed': GraphQLField(GraphQLString)
        }
    )

    QueryType = GraphQLObjectType(
        name='Query',
        fields={
            'getTodos': GraphQLField(
                GraphQLList(TodoType),
                resolve=lambda obj, info: todo_manager.todos
            )
        }
    )

    MutationType = GraphQLObjectType(
        name='Mutation',
        fields={
            'addTodo': GraphQLField(
                TodoType,
                args={
                    'title': GraphQLArgument(GraphQLString),
                    'description': GraphQLArgument(GraphQLString),
                    'priority': GraphQLArgument(GraphQLString),
                    'due_date': GraphQLArgument(GraphQLString),
                },
                resolve=lambda obj, info, **kwargs: 
                    todo_manager.add_todo(
                        kwargs['title'], 
                        kwargs['description'], 
                        kwargs.get('priority', 'medium'),
                        kwargs.get('due_date', datetime.now(pytz.UTC).isoformat())
                    )
            ),
            'deleteTodo': GraphQLField(
                GraphQLString,
                args={'id': GraphQLArgument(GraphQLString)},
                resolve=lambda obj, info, id: todo_manager.delete_todo(id)
            ),
            'updateTodoStatus': GraphQLField(
                TodoType,
                args={
                    'id': GraphQLArgument(GraphQLString),
                    'completed': GraphQLArgument(GraphQLString)
                },
                resolve=lambda obj, info, id, completed: 
                    todo_manager.update_todo_status(id, completed == 'true')
            )
        }
    )

    return GraphQLSchema(query=QueryType, mutation=MutationType)

def create_todo_visualizations(todo_manager):
    """Create visualizations for todo status and priority"""
    data = todo_manager.get_todos_data_for_visualization()

    # Status Pie Chart
    st.subheader("Todo Status Overview")
    status_fig = px.pie(
        data['status'], 
        values='Count', 
        names='Status', 
        title='Todo Completion Status',
        color='Status',
        color_discrete_map={'Completed': 'green', 'Pending': 'red'}
    )
    st.plotly_chart(status_fig)

    # Priority Bar Chart
    st.subheader("Todo Priority Breakdown")
    priority_data = []
    for priority, counts in data['priority'].items():
        priority_data.extend([
            {'Priority': priority.capitalize(), 'Status': 'Completed', 'Count': counts['completed']},
            {'Priority': priority.capitalize(), 'Status': 'Pending', 'Count': counts['pending']}
        ])
    
    priority_df = pd.DataFrame(priority_data)
    priority_fig = px.bar(
        priority_df, 
        x='Priority', 
        y='Count', 
        color='Status',
        title='Todos by Priority and Status',
        barmode='group'
    )
    st.plotly_chart(priority_fig)

def authenticate(username, password):
    """Simple authentication"""
    users = {
        'admin': {'password': 'admin123', 'role': 'admin'},
        'user': {'password': 'user123', 'role': 'user'}
    }
    
    if username in users and users[username]['password'] == password:
        return {
            'token': str(uuid.uuid4()),
            'role': users[username]['role']
        }
    return None

def main():
    st.set_page_config(
        page_title="Todo Manager",
        page_icon=":memo:",
        layout="wide"
    )

    # def local_css(file_name):
    #     with open(file_name) as f:
    #         st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

    # # In your main() function, before creating the app layout
    # local_css("custom.css") 

    # Initialize todo manager
    if 'todo_manager' not in st.session_state:
        st.session_state.todo_manager = TodoManager()

    # Initialize notification manager
    if 'notification_manager' not in st.session_state:
        st.session_state.notification_manager = NotificationManager(st.session_state.todo_manager)

    # Authentication
    if 'user' not in st.session_state:
        st.title("🔐 Todo Manager - Login")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.image("https://img.icons8.com/fluency/240/todo-list.png")
        
        with col2:
            with st.form("login_form"):
                username = st.text_input("📧 Username")
                password = st.text_input("🔑 Password", type="password")
                login_button = st.form_submit_button("Login")

                if login_button:
                    auth_result = authenticate(username, password)
                    if auth_result:
                        st.session_state.user = auth_result
                        st.success("Logged in successfully!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        return

    # Notification Controls
    st.sidebar.header("🔔 Notification Settings")
    
    # Start/Stop Notification Service
    if 'notification_service_running' not in st.session_state:
        st.session_state.notification_service_running = False

    def toggle_notification_service():
        if not st.session_state.notification_service_running:
            st.session_state.notification_manager.start_notification_service(interval=60)  # Check every minute
            st.session_state.notification_service_running = True
            st.sidebar.success("Notification service started")
        else:
            st.session_state.notification_manager.stop_notification_service()
            st.session_state.notification_service_running = False
            st.sidebar.warning("Notification service stopped")

    # Notification service toggle
    st.sidebar.button(
        "🟢 Start Notifications" if not st.session_state.notification_service_running 
        else "🔴 Stop Notifications", 
        on_click=toggle_notification_service
    )

    # Manual notification check
    if st.sidebar.button("🔍 Check Due Todos"):
        st.session_state.notification_manager.check_due_todos()
        st.sidebar.success("Checked for due todos and sent notifications")

    # Main Application
    st.title(f"📋 Todo Manager - Welcome, {st.session_state.user.get('role', 'User')}")

    # Create GraphQL schema
    schema = get_graphql_schema(st.session_state.todo_manager)

    # Filtering and Sorting
    st.sidebar.header("🔍 Todo Filters")
    filter_option = st.sidebar.selectbox(
        "Filter Todos", 
        ["All", "Active", "Completed"]
    )

    sort_option = st.sidebar.selectbox(
        "Sort By", 
        ["Default", "Priority", "Due Date"]
    )

    # Add Todo Form
    with st.expander("➕ Add New Todo", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            title = st.text_input("Title")
        with col2:
            priority = st.selectbox("Priority", ["low", "medium", "high"])
        with col3:
            due_date = st.date_input("Due Date")

        col4, col5 = st.columns(2)
        with col4:
            category = st.selectbox("Category", st.session_state.todo_manager.categories)
        with col5:
            description = st.text_area("Description")

        col6, col7 = st.columns(2)
        with col6:
            reminder_date = st.date_input("Reminder Date")
        with col7:
            reminder_time = st.time_input("Reminder Time")
        
        if st.button("Add Todo"):
            if title:
                reminder_datetime = datetime.combine(reminder_date, reminder_time).isoformat() if reminder_date and reminder_time else None
                todo = st.session_state.todo_manager.add_todo(
                    title, 
                    description, 
                    priority, 
                    due_date.isoformat(), 
                    category,
                    reminder_datetime
                )
                st.success(f"Todo '{title}' added successfully!")

    # Display Todos
    st.header("📝 My Todos")
    
    # Apply filters and sorting
    todos = st.session_state.todo_manager.get_todos()
    
    if filter_option == "Active":
        todos = [todo for todo in todos if not todo['completed']]
    elif filter_option == "Completed":
        todos = [todo for todo in todos if todo['completed']]
    
    if sort_option == "Priority":
        todos.sort(key=lambda x: ['low', 'medium', 'high'].index(x['priority']))
    elif sort_option == "Due Date":
        todos.sort(key=lambda x: x['due_date'])
    

    colA, colB = st.columns(2)
    with colA:
        st.write("📝 Pending Todos")
        pending_todos = [todo for todo in todos if not todo['completed']]
        if pending_todos:
            for todo_index, todo in enumerate(pending_todos, start=1):
                # use unique key for each todo
                unique_key = f"{todo['id']}_{todo_index}"   
                # Use a unique container for each todo
                todo_container = st.container()
                with todo_container:
                    # Unique keys using a combination of ID, index, and a timestamp
                    unique_key = f"{todo['id']}_{todo_index}_{hash(todo['created_at'])}"
                    
                    st.markdown(f"**{todo['title']}**")
                    # st.markdown(f"*{todo['description']}*")
                    col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
                    
                    with col1:
                        st.text(f"Description: {todo['description']}")
                        st.text(f"Priority: {todo['priority'].capitalize()}")
                        st.text(f"Due: {todo['due_date']}")
                
                    with col2:
                        # Use unique key for checkbox
                        completed = st.checkbox(
                            "Completed", 
                            value=todo['completed'], 
                            key=f"complete_{unique_key}"
                        )
                        if completed != todo['completed']:
                            mutation = parse(f"""
                            mutation {{
                                updateTodoStatus(
                                    id: "{todo['id']}", 
                                    completed: "{str(completed).lower()}"
                                ) {{
                                    id
                                    completed
                                }}
                            }}
                            """)
                            execute(schema, mutation)
                    
                    with col3:
                        # Use unique key for delete button
                        if st.button(f"Delete {todo['title']}", key=f"delete_{unique_key}"):
                            mutation = parse(f"""
                            mutation {{
                                deleteTodo(id: "{todo['id']}")
                            }}
                            """)
                            execute(schema, mutation)
                            # Use specific Streamlit method to handle rerun
                            st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("No todos found. Add a new todo to get started!")
    
    with colB:
        st.write("✅ Completed Todos")
        completed_todos = [todo for todo in todos if todo['completed']]
        if completed_todos:
            for todo_index, todo in enumerate(completed_todos, start=1):
                # use unique key for each todo
                unique_key = f"{todo['id']}_{todo_index}"
                # Use a unique container for each todo
                todo_container = st.container()
                with todo_container:
                    
                    st.markdown(f"~~{todo['title']}~~")
                    st.markdown(f"*{todo['description']}*")

                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.markdown(f"**Priority:** {todo['priority'].capitalize()}")
                    with col_b:
                        st.markdown(f"**Category:** {todo['category']}")
                    with col_c:
                        st.markdown(f"**Due:** {todo['due_date']}")
                    
                    # Use unique key for delete button
                    if st.button(f"Delete {todo['title']}", key=f"delete_{unique_key}"):
                        # Remove todo
                        # st.session_state.todo_manager.todos = [
                        #     t for t in st.session_state.todo_manager.todos 
                        #     if t['id'] != todo['id']
                        # ]
                        # st.rerun()
                        mutation = parse(f"""
                        mutation {{
                            deleteTodo(id: "{todo['id']}")
                        }}
                        """)
                        execute(schema, mutation)
                        st.rerun()

                    st.markdown("---")
        else:
            st.info("No completed todos yet!")
    
    # Visualization Section
    st.sidebar.header("📊 Todo Analytics")
    if st.sidebar.checkbox("Show Todo Analytics"):
        create_todo_visualizations(st.session_state.todo_manager)

    # Logout button
    if st.sidebar.button("🚪 Logout"):
        # Stop notification service if running
        if st.session_state.notification_service_running:
            st.session_state.notification_manager.stop_notification_service()
        
        # Clear session state
        del st.session_state.user
        st.rerun()

if __name__ == "__main__":
    main()