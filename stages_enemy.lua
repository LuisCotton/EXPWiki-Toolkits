--[[
怪物登场关卡的渲染模块（上传为 Module:StagesEnemy），读取 EnemyStages.json。

用法：
    {{#invoke:StagesEnemy|getEnemyStages|{{PAGENAME}}}}   输出该怪物的登场关卡
    {{#invoke:StagesEnemy|getStages|怪物}}                 输出全怪物总表

参数可以省略：省略时取当前页面标题（自动去掉命名空间前缀）作为怪物名。
匹配顺序为 怪物中文名 -> 实体ID，两者都不区分大小写。

数据由 stages_enemy.py 从 stages.xml 生成，只包含自然出怪表。
旗帜事件等「特殊生成」的怪物、以及没有 <spawns> 节点的解谜关不在其中。
]]

local p = {}

local dataCache
local lookupCache

local function loadData()
    if dataCache then
        return dataCache
    end
    local ok, data = pcall(mw.loadJsonData, 'EnemyStages.json')
    if not ok or type(data) ~= 'table' then
        local title = mw.title.new('EnemyStages.json')
        if not title or not title.exists then
            return nil
        end
        ok, data = pcall(mw.text.jsonDecode, title:getContent() or '')
        if not ok or type(data) ~= 'table' then
            return nil
        end
    end
    dataCache = data.monsters or data
    return dataCache
end

-- 建立 名字/ID -> 怪物记录 的索引。同一个怪物名可能对应多条记录
-- （来自不同实体 ID 或不同英文名），合并它们的关卡列表。
-- 同一个怪物名可能对应多条记录（来自不同实体 ID 或英文名），
-- 这里把它们的关卡列表按分组合并去重。
local function mergeMonster(groups, order, monster, key)
    local group = groups[key]
    if not group then
        group = { id = monster.id, name = monster.name, categories = {}, order = {} }
        groups[key] = group
        table.insert(order, key)
    end

    for _, category in ipairs(monster.stagesByCategory or {}) do
        local slot = group.categories[category.category]
        if not slot then
            slot = {
                category = category.category,
                chapter = category.chapter,
                stages = {},
                seen = {},
            }
            group.categories[category.category] = slot
            table.insert(group.order, category.category)
        end
        for _, stage in ipairs(category.stages or {}) do
            if stage.link and not slot.seen[stage.link] then
                slot.seen[stage.link] = true
                table.insert(slot.stages, stage)
            end
        end
    end
end

local function addKeys(keys, key)
    if type(key) == 'string' and key ~= '' then
        keys[key] = true
        keys[key:lower()] = true
    end
end

local function loadLookup()
    if lookupCache then
        return lookupCache
    end
    local data = loadData()
    if not data then
        return nil
    end

    local groups = {}
    local order = {}
    for _, monster in ipairs(data) do
        local keys = {}
        addKeys(keys, monster.name)
        addKeys(keys, monster.id)
        for key in pairs(keys) do
            mergeMonster(groups, order, monster, key)
        end
    end

    lookupCache = groups
    return lookupCache
end

local function trim(value)
    return mw.text.trim(tostring(value or ''))
end

-- 取反模式：章节分组的显示名就是章节名，直接加粗；
-- 非章节分组（小游戏/解密模式等）前面补一个换行，让列表从新的一行开始。
local function heading(group)
    if group.chapter then
        return "'''" .. group.category .. "'''："
    end
    return "<br>'''" .. group.category .. "'''："
end

local function groupText(group)
    local links = {}
    for _, stage in ipairs(group.stages) do
        table.insert(links, '[[' .. stage.link .. ']]')
    end
    return heading(group) .. table.concat(links, '、')
end

local function monsterText(monster)
    local result = {}
    for _, name in ipairs(monster.order) do
        local group = monster.categories[name]
        if #group.stages > 0 then
            table.insert(result, groupText(group))
        end
    end
    if #result == 0 then
        return nil
    end
    return table.concat(result, '\n')
end

-- 供怪物页面「登场关卡」章节调用：{{#invoke:StagesEnemy|getEnemyStages|{{PAGENAME}}}}
function p.getEnemyStages(frame)
    local lookup = loadLookup()
    if not lookup then
        return '错误：无法加载 [[EnemyStages.json]]'
    end

    local key = trim(frame.args[1])
    if key == '' then
        local parent = frame:getParent()
        if parent then
            key = trim(parent:getTitle():gsub('^[^:]+:', ''))
        end
    end
    if key == '' then
        return '错误：请提供怪物名或ID。'
    end

    local monster = lookup[key] or lookup[key:lower()]
    if not monster then
        return '没有找到「' .. key .. '」的登场关卡数据。'
    end

    local text = monsterText(monster)
    if not text then
        return '「' .. key .. '」没有可列出的登场关卡。'
    end
    return text
end

-- 传入「怪物」时输出全怪物总表，便于一次核对整体数据。
-- 每格用 <br> 连接，避免定义列表里换行把布局撑坏。
local function compactGroupText(group)
    local links = {}
    for _, stage in ipairs(group.stages) do
        table.insert(links, '[[' .. stage.link .. ']]')
    end
    return "'''" .. group.category .. "'''：" .. table.concat(links, '<br>')
end

local function allTable(data)
    local result = {
        '{| class="wikitable sortable"',
        '|-',
        '! 怪物 !! 登场关卡数 !! 登场关卡',
    }
    for _, monster in ipairs(data) do
        local cells = {}
        for _, category in ipairs(monster.stagesByCategory or {}) do
            if #(category.stages or {}) > 0 then
                table.insert(cells, compactGroupText(category))
            end
        end
        table.insert(result, '|-')
        table.insert(result, string.format(
            '| [[%s]] || %s || %s',
            monster.name, tostring(monster.stageCount or 0), table.concat(cells, '<br>')
        ))
    end
    table.insert(result, '|}')
    return table.concat(result, '\n')
end

function p.getAllEnemyStages(frame)
    local data = loadData()
    if not data then
        return '错误：无法加载 [[EnemyStages.json]]'
    end
    local key = trim(frame.args[1])
    if key == '怪物' or key == '总表' or key == 'all' then
        return allTable(data)
    end
    return '错误：本函数用于输出总表，请传「怪物」作为参数。'
end

-- 传「怪物」时自动走总表，其余参数走单怪物查询。
function p.getStages(frame)
    local key = trim(frame.args[1])
    if key == '怪物' or key == '总表' or key == 'all' then
        return p.getAllEnemyStages(frame)
    end
    return p.getEnemyStages(frame)
end

return p
