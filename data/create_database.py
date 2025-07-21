import sqlite3
import random
from datetime import datetime, timedelta
from faker import Faker

# Inicializa o Faker
fake = Faker('pt_BR')

# Conecta ao banco de dados (ou cria se não existir)
conn = sqlite3.connect('data/database.db')
cursor = conn.cursor()

# --- Criação das Tabelas ---
print("Criando tabelas...")
cursor.execute('''
DROP TABLE IF EXISTS itens_pedido;
''')
cursor.execute('''
DROP TABLE IF EXISTS pedidos;
''')
cursor.execute('''
DROP TABLE IF EXISTS produtos;
''')
cursor.execute('''
DROP TABLE IF EXISTS clientes;
''')

cursor.execute('''
CREATE TABLE clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    idade INTEGER,
    data_cadastro DATE
);
''')

cursor.execute('''
CREATE TABLE produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    categoria TEXT NOT NULL,
    preco REAL NOT NULL
);
''')

cursor.execute('''
CREATE TABLE pedidos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,
    data_pedido DATE,
    status TEXT,
    FOREIGN KEY (cliente_id) REFERENCES clientes (id)
);
''')

cursor.execute('''
CREATE TABLE itens_pedido (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id INTEGER,
    produto_id INTEGER,
    quantidade INTEGER,
    preco_unitario REAL,
    FOREIGN KEY (pedido_id) REFERENCES pedidos (id),
    FOREIGN KEY (produto_id) REFERENCES produtos (id)
);
''')
print("Tabelas criadas com sucesso!")

# --- Inserção de Dados Falsos ---
print("Inserindo dados falsos...")

# Clientes
clientes_ids = []
for _ in range(20):
    cursor.execute("INSERT INTO clientes (nome, email, idade, data_cadastro) VALUES (?, ?, ?, ?)",
                   (fake.name(), fake.email(), random.randint(18, 70), fake.date_between(start_date='-2y', end_date='today')))
    clientes_ids.append(cursor.lastrowid)

# Produtos
produtos = [
    ('Laptop', 'Eletrônicos', 4500.00), ('Mouse', 'Eletrônicos', 150.00),
    ('Teclado', 'Eletrônicos', 250.00), ('Monitor', 'Eletrônicos', 1200.00),
    ('Cadeira Gamer', 'Móveis', 1500.00), ('Mesa de Escritório', 'Móveis', 800.00),
    ('Livro de Ficção', 'Livros', 45.00), ('Livro Técnico', 'Livros', 120.00)
]
produtos_ids = []
for produto in produtos:
    cursor.execute("INSERT INTO produtos (nome, categoria, preco) VALUES (?, ?, ?)", produto)
    produtos_ids.append(cursor.lastrowid)

# Pedidos e Itens de Pedido
for i in range(50):
    cliente_id = random.choice(clientes_ids)
    data_pedido = fake.date_between(start_date='-1y', end_date='today')
    status = random.choice(['Entregue', 'Pendente', 'Cancelado'])
    cursor.execute("INSERT INTO pedidos (cliente_id, data_pedido, status) VALUES (?, ?, ?)",
                   (cliente_id, data_pedido, status))
    pedido_id = cursor.lastrowid

    # Adiciona itens ao pedido
    for _ in range(random.randint(1, 4)):
        produto_info = random.choice(list(zip(produtos_ids, produtos)))
        produto_id = produto_info[0]
        preco_unitario = produto_info[1][2]
        quantidade = random.randint(1, 3)
        cursor.execute("INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                       (pedido_id, produto_id, quantidade, preco_unitario))

conn.commit()
conn.close()

print("Banco de dados 'database.db' criado e populado com sucesso!")