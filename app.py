import streamlit as st
import uuid
from graphql import (GraphQLObjectType, GraphQLString, GraphQLSchema, 
                     GraphQLField, GraphQLList, GraphQLArgument, execute)
from graphql.language import parse
from datetime import datetime
import pytz

class TodoManager:
    def __init__(self):
        self.todos = []

    def add_todo(self, title, description, priority, due_date):
        """Add a new todo with more detailed information"""
        todo = {
            'id': str(uuid.uuid4()),  # Use UUID for unique IDs
            'title': title,
            'description': description,
            'priority': priority,
            'due_date': due_date,
            'created_at': datetime.now(pytz.UTC).isoformat(),
            'completed': False
        }
        self.todos.append(todo)
        return todo

    def get_todos(self, filter_completed=None, sort_by=None):
        """Retrieve todos with optional filtering and sorting"""
        filtered_todos = self.todos
        
        if filter_completed is not None:
            filtered_todos = [todo for todo in filtered_todos if todo['completed'] == filter_completed]
        
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
                resolve=lambda obj, info: todo_manager.get_todos()
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

def authenticate(username, password):
    """Enhanced authentication with more robust checks"""
    # In a real-world scenario, replace with secure Keycloak authentication
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

    # Initialize todo manager in session state
    if 'todo_manager' not in st.session_state:
        st.session_state.todo_manager = TodoManager()

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
                        st.experimental_rerun()
                    else:
                        st.error("Invalid credentials")
        return

    # Main Application
    st.title(f"📋 Todo Manager - Welcome, {st.session_state.user.get('role', 'User')}")

    # Sidebar for filtering and actions
    st.sidebar.title("🔍 Todo Controls")
    filter_option = st.sidebar.selectbox(
        "Filter Todos", 
        ["All", "Active", "Completed"]
    )

    sort_option = st.sidebar.selectbox(
        "Sort By", 
        ["Default", "Priority", "Due Date"]
    )

    # Create GraphQL schema
    schema = get_graphql_schema(st.session_state.todo_manager)

    # Add Todo Form
    with st.expander("➕ Add New Todo", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            title = st.text_input("Title")
        with col2:
            priority = st.selectbox("Priority", ["low", "medium", "high"])
        with col3:
            due_date = st.date_input("Due Date")

        description = st.text_area("Description")
        
        if st.button("Add Todo"):
            if title:
                mutation = parse(f"""
                mutation {{
                    addTodo(
                        title: "{title}", 
                        description: "{description}", 
                        priority: "{priority}",
                        due_date: "{due_date}"
                    ) {{
                        id
                        title
                        description
                    }}
                }}
                """)
                execute(schema, mutation)
                st.success("Todo added successfully!")

    # Display Todos
    st.header("📝 My Todos")
    
    # Apply filters and sorting
    todos = st.session_state.todo_manager.todos
    
    if filter_option == "Active":
        todos = [todo for todo in todos if not todo['completed']]
    elif filter_option == "Completed":
        todos = [todo for todo in todos if todo['completed']]
    
    if sort_option == "Priority":
        todos.sort(key=lambda x: ['low', 'medium', 'high'].index(x['priority']))
    elif sort_option == "Due Date":
        todos.sort(key=lambda x: x['due_date'])

    if todos:
        for todo in todos:
            with st.container():
                col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
                
                with col1:
                    st.markdown(f"**{todo['title']}**")
                    st.text(f"Description: {todo['description']}")
                    st.text(f"Priority: {todo['priority'].capitalize()}")
                    st.text(f"Due: {todo['due_date']}")
                
                with col2:
                    completed = st.checkbox(
                        "Completed", 
                        value=todo['completed'], 
                        key=f"complete_{todo['id']}"
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
                    if st.button(f"Delete {todo['title']}", key=f"delete_{todo['id']}"):
                        mutation = parse(f"""
                        mutation {{
                            deleteTodo(id: "{todo['id']}")
                        }}
                        """)
                        execute(schema, mutation)
                        st.experimental_rerun()
                
                st.markdown("---")
    else:
        st.info("No todos found. Add a new todo to get started!")

    # Logout button
    if st.sidebar.button("🚪 Logout"):
        del st.session_state.user
        st.experimental_rerun()

if __name__ == "__main__":
    main()