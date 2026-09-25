local p = {}

local rootCache
local lookupCache

local function loadRoot()
    if rootCache then
        return rootCache
    end
    local ok, data = pcall(mw.loadJsonData, 'Stages.json')
    if not ok or type(data) ~= 'table' then
        local title = mw.title.new('Stages.json')
        if not title or not title.exists then
            return nil
        end
        ok, data = pcall(mw.text.jsonDecode, title:getContent() or '')
        if not ok or type(data) ~= 'table' then
            return nil
        end
    end
    rootCache = data
    return rootCache
end

local function loadStages()
    local data = loadRoot()
    if not data then return nil end
    return data.entries or data
end

local function loadMonsters()
    local data = loadRoot()
    if not data or type(data.monsters) ~= 'table' then return nil end
    return data.monsters
end

local function keyOf(frame)
    local key = frame.args[1]
    if not key or key == '' then
        local parent = frame:getParent()
        if parent then
            key = parent:getTitle():gsub('^[^:]+:', '')
        end
    end
    return key
end

local function matchStage(stage, key)
    return stage.displayName == key or stage.name == key or stage.id == key
end

local function spawnName(spawn)
    return spawn.name or spawn.id or ''
end

local function stageText(stage)
    local spawns = type(stage.spawns) == 'table' and stage.spawns or {}
    local links = {}
    local icons = {}
    for _, spawn in ipairs(spawns) do
        local name = spawnName(spawn)
        if name ~= '' then
            table.insert(links, '[[' .. name .. ']]')
            if not spawn.noIcon then
                table.insert(icons, '{{Spr_E|' .. name .. '}}')
            end
        end
    end

    local spawnText = #links > 0 and table.concat(links, '、') or '无'
    local result = {
        '===自然生成===',
        '默认出怪表：' .. spawnText,
    }
    if #icons > 0 then
        table.insert(result, '')
        for _, icon in ipairs(icons) do
            table.insert(result, icon)
        end
    end
    return table.concat(result, '\n')
end

local function stageResult(frame, key)
    local data = loadStages()
    if not data then
        return '错误：无法加载 [[Stages.json]]'
    end
    for _, stage in ipairs(data) do
        if matchStage(stage, key) then
            return frame:preprocess(stageText(stage))
        end
    end
    return nil
end

local function trim(value)
    return mw.text.trim(tostring(value or ''))
end

local function addLookupKey(lookup, key, monster)
    if type(key) == 'string' and key ~= '' then
        lookup[key] = monster
        lookup[key:lower()] = monster
    end
end

local function loadMonsterLookup()
    if lookupCache then return lookupCache end
    local monsters = loadMonsters()
    if not monsters then return nil end
    local lookup = {}
    for _, monster in ipairs(monsters) do
        addLookupKey(lookup, monster.name, monster)
        for _, id in ipairs(monster.ids or {}) do
            addLookupKey(lookup, id, monster)
        end
    end
    lookupCache = lookup
    return lookupCache
end

local function enemyGroupText(group)
    local links = {}
    for _, stage in ipairs(group.stages or {}) do
        table.insert(links, '[[' .. stage.link .. ']]')
    end
    return "'''" .. group.category .. "'''：" .. table.concat(links, '、')
end

local function enemyText(monster)
    local result = {}
    for _, group in ipairs(monster.stagesByCategory or {}) do
        if #(group.stages or {}) > 0 then
            table.insert(result, enemyGroupText(group))
        end
    end
    if #result == 0 then return nil end
    return table.concat(result, '\n')
end

local function enemyResult(key)
    local lookup = loadMonsterLookup()
    if not lookup then
        return '错误：无法从 [[Stages.json]] 加载怪物登场数据。'
    end
    local monster = lookup[key] or lookup[key:lower()]
    if not monster then
        return nil
    end
    local text = enemyText(monster)
    if not text then
        return '「' .. key .. '」没有可列出的登场关卡。'
    end
    return text
end

local function compactEnemyGroupText(group)
    local links = {}
    for _, stage in ipairs(group.stages or {}) do
        table.insert(links, '[[' .. stage.link .. ']]')
    end
    return "'''" .. group.category .. "'''：" .. table.concat(links, '<br>')
end

local function allEnemyTable(monsters)
    local result = {
        '{| class="wikitable sortable"',
        '|-',
        '! 怪物 !! 登场关卡数 !! 登场关卡',
    }
    for _, monster in ipairs(monsters) do
        local cells = {}
        for _, category in ipairs(monster.stagesByCategory or {}) do
            if #(category.stages or {}) > 0 then
                table.insert(cells, compactEnemyGroupText(category))
            end
        end
        table.insert(result, '|-')
        table.insert(result, string.format(
            '| [[%s]] || %s || %s',
            monster.name,
            tostring(monster.stageCount or 0),
            table.concat(cells, '<br>')
        ))
    end
    table.insert(result, '|}')
    return table.concat(result, '\n')
end

local function allEnemyResult()
    local monsters = loadMonsters()
    if not monsters then
        return '错误：无法从 [[Stages.json]] 加载怪物登场数据。'
    end
    return allEnemyTable(monsters)
end

function p.getStages(frame)
    local key = trim(keyOf(frame))
    if key == '' then
        return '错误：请提供关卡名、关卡ID、怪物名或怪物ID。'
    end
    if key == '怪物' or key == '总表' or key == 'all' then
        return allEnemyResult()
    end
    local result = stageResult(frame, key)
    if result then return result end
    result = enemyResult(key)
    if result then return result end
    return '没有找到「' .. key .. '」对应的关卡或怪物。'
end

return p