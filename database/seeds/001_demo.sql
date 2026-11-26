-- Fictional demo data. No real student accounts or real project claims.
INSERT INTO users (id,email,password_hash,name,bio,institute,skills,role) VALUES
(1001,'author@example.com','scrypt$382c59827ffd125b61987fc710508bb6$40811d33fbc6b73f293d2f2bcfdfc8b034427be7b1639cdfcd279ee77a1ac334ea0b04098861e006c44f9e4c461baa115d82bcfcdba161db8c21c6bb5b8d7f47','Тестовый автор','Демонстрационный профиль автора проектов.','Тестовая учебная группа','["Python", "Организация"]','student'),
(1002,'student@example.com','scrypt$382c59827ffd125b61987fc710508bb6$40811d33fbc6b73f293d2f2bcfdfc8b034427be7b1639cdfcd279ee77a1ac334ea0b04098861e006c44f9e4c461baa115d82bcfcdba161db8c21c6bb5b8d7f47','Тестовый участник','Хочу попробовать себя в командной разработке. Тестовый профиль.','Тестовая учебная группа','["JavaScript", "React"]','student'),
(1003,'moderator@example.com','scrypt$382c59827ffd125b61987fc710508bb6$40811d33fbc6b73f293d2f2bcfdfc8b034427be7b1639cdfcd279ee77a1ac334ea0b04098861e006c44f9e4c461baa115d82bcfcdba161db8c21c6bb5b8d7f47','Тестовый модератор','Демонстрационный модератор.','','[]','moderator'),
(1004,'member@example.com','scrypt$382c59827ffd125b61987fc710508bb6$40811d33fbc6b73f293d2f2bcfdfc8b034427be7b1639cdfcd279ee77a1ac334ea0b04098861e006c44f9e4c461baa115d82bcfcdba161db8c21c6bb5b8d7f47','Тестовый инженер','Демонстрационный профиль участника.','','["CAD", "Python"]','student')
ON CONFLICT (id) DO NOTHING;
INSERT INTO projects (id,owner_id,title,description,category,format,skills,status,moderation_note,is_demo) VALUES
(1101,1001,'Орбитальная лаборатория','Создаём учебную модель спутника и панель телеметрии. Задачи: спроектировать корпус, смоделировать датчики и собрать прототип интерфейса. Результат — демонстрационный стенд. Это вымышленный тестовый проект.','Инженерия','Гибрид','["CAD", "Python"]','published','',true),
(1102,1001,'Навигатор добрых дел','Разрабатываем учебный каталог волонтёрских инициатив. Нужно описать сценарии, подготовить дизайн и создать интерфейс поиска. Результат — работающий прототип. Это вымышленный тестовый проект.','Социальные проекты','Онлайн','["React", "UX"]','published','',true),
(1103,1001,'Данные о городе','Исследуем синтетические данные о городской среде. Планируем подготовить набор данных, провести анализ и сделать интерактивные графики. Это вымышленный тестовый проект, реальные исследования не заявляются.','Наука','Гибрид','["Python", "Анализ данных"]','published','',true),
(1104,1001,'Студенческая мастерская','Создаём учебную платформу обмена навыками между студентами. В команде нужны разработчики интерфейса и API. Результат — каталог учебных встреч. Это вымышленный тестовый проект.','IT','Онлайн','["JavaScript", "React", "FastAPI"]','published','',true),
(1105,1001,'Дизайн без барьеров','Исследуем доступность учебных интерфейсов на вымышленных примерах. Подготовим прототип, проверим контраст и сценарии клавиатурной навигации. Это тестовый проект для демонстрации каталога.','Дизайн','Очно','["Figma", "UX"]','published','',true),
(1106,1001,'Робот для учебной трассы','Собираем учебный прототип робота для движения по линии. Требуется написать алгоритм управления и подготовить схему датчиков. Это тестовый проект, участия в реальных соревнованиях не заявлено.','Инженерия','Очно','["C++", "Электроника"]','published','',true),
(1107,1001,'Проект на проверке','Тестовая публикация для демонстрации кабинета модератора. Нужно проверить описание и требования к участникам, затем опубликовать или отклонить заявку.','IT','Онлайн','["Python"]','pending','',true)
ON CONFLICT (id) DO NOTHING;
INSERT INTO vacancies (id,project_id,title,requirements,capacity) VALUES
(1201,1101,'Инженер-конструктор','Основы CAD. Готовность обсуждать и проверять решения.',2),
(1202,1102,'Frontend-разработчик','Базовое знание JavaScript и React. Можно без опыта.',2),
(1203,1103,'Аналитик данных','Основы Python, интерес к анализу данных.',2),
(1204,1104,'React-разработчик','React, работа с REST API, командная работа.',2),
(1205,1105,'UX-дизайнер','Работа в Figma. Интерес к доступности интерфейсов.',1),
(1206,1106,'Разработчик C++','Базовые знания C++ и электроники.',2),
(1207,1107,'Python-разработчик','Основы Python и интерес к серверной разработке.',1)
ON CONFLICT (id) DO NOTHING;
INSERT INTO applications (id,vacancy_id,user_id,message,status) VALUES
(1301,1204,1002,'Это тестовый отклик. Хочу помочь с React и интерфейсом каталога.','pending'),
(1302,1201,1004,'Это тестовый отклик принятого участника команды.','accepted')
ON CONFLICT (id) DO NOTHING;
SELECT setval(pg_get_serial_sequence('users','id'), GREATEST((SELECT COALESCE(MAX(id),1) FROM users),1));
SELECT setval(pg_get_serial_sequence('projects','id'), GREATEST((SELECT COALESCE(MAX(id),1) FROM projects),1));
SELECT setval(pg_get_serial_sequence('vacancies','id'), GREATEST((SELECT COALESCE(MAX(id),1) FROM vacancies),1));
SELECT setval(pg_get_serial_sequence('applications','id'), GREATEST((SELECT COALESCE(MAX(id),1) FROM applications),1));
