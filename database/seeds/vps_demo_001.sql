BEGIN;
-- Runs once per VPS database in the same transaction as the migration record.
DO $$
DECLARE
    sample record;
    suffix integer;
    login text;
    author_id integer;
    new_project_id integer;
BEGIN
    FOR sample IN SELECT * FROM (VALUES
        ('engineer', 'Арина Соколова', 'Собираю учебные макеты и работаю в CAD.',
         'Орбитальная лаборатория', 'Собираем макет спутника для учебного стенда. Ищем инженера, который спроектирует крепления датчиков и поможет собрать корпус.',
         'Инженерия', 'Гибрид', '["CAD", "Электроника"]', 'Инженер-конструктор', 'Основы CAD и интерес к прототипированию.'),
        ('designer', 'Михаил Воронов', 'Проектирую интерфейсы и изучаю доступность сайтов.',
         'Навигатор добрых дел', 'Делаем каталог студенческих волонтёрских инициатив. Нужно нарисовать карточки мероприятий и проверить, удобно ли находить подходящие проекты.',
         'Социальные проекты', 'Онлайн', '["Figma", "UX"]', 'Дизайнер интерфейсов', 'Опыт работы в Figma или примеры учебных макетов.'),
        ('analyst', 'Полина Белова', 'Изучаю Python и визуализацию данных.',
         'Город в данных', 'Готовим интерактивную карту на учебном наборе данных о городской среде. Ищем участника для очистки таблиц и построения графиков.',
         'Наука', 'Онлайн', '["Python", "Анализ данных"]', 'Аналитик данных', 'Базовые навыки Python и работы с таблицами.')
    ) AS samples(slug, name, bio, title, description, category, format, skills, vacancy, requirements)
    LOOP
        suffix := 0;
        LOOP
            login := 'demo.' || sample.slug || CASE WHEN suffix = 0 THEN '' ELSE '.' || suffix END || '@example.com';
            INSERT INTO users (email, password_hash, name, bio, skills)
            VALUES (login, current_setting('mai.demo_password_hash'), sample.name, 'Тестовый профиль. ' || sample.bio, sample.skills)
            ON CONFLICT (email) DO NOTHING RETURNING id INTO author_id;
            EXIT WHEN author_id IS NOT NULL;
            suffix := suffix + 1;
        END LOOP;

        INSERT INTO projects (owner_id, title, description, category, format, skills, status, is_demo, team_contact)
        VALUES (author_id, sample.title, sample.description, sample.category, sample.format, sample.skills, 'published', true, login)
        RETURNING id INTO new_project_id;
        INSERT INTO vacancies (project_id, title, requirements, capacity)
        VALUES (new_project_id, sample.vacancy, sample.requirements, 2);
    END LOOP;
END;
$$;
COMMIT;
