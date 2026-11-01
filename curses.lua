local p = {}

local dataCache

local function loadData()
    if dataCache then
        return dataCache
    end

    local ok, data = pcall(mw.loadJsonData, 'Module:Curses.json')
    if not ok or type(data) ~= 'table' then
        local title = mw.title.new('Module:Curses.json')
        if not title or not title.exists then
            return nil
        end
        ok, data = pcall(mw.text.jsonDecode, title:getContent() or '')
        if not ok or type(data) ~= 'table' then
            return nil
        end
    end

    dataCache = data.curses or data
    return dataCache
end

local function tableText(value)
    local text = tostring(value or '')
    text = text:gsub('|', '{{!}}')
    text = text:gsub('\\n', '<br>')
    text = text:gsub('\r\n', '<br>')
    text = text:gsub('[\r\n]', '<br>')
    return text
end

function p.getCurses(frame)
    local data = loadData()
    if not data then
        return '错误：无法加载 [[Module:Curses.json]]'
    end

    local result = {
        '{| class="wikitable"',
        '|-',
        '! 诅咒名称 !! 效果',
    }

    for _, curse in ipairs(data) do
        if type(curse) == 'table' then
            table.insert(result, '|-')
            table.insert(result, '| ' .. tableText(curse.name) .. ' || ' .. tableText(curse.effect))
        end
    end

    table.insert(result, '|}')
    return table.concat(result, '\n')
end

function p.main(frame)
    return p.getCurses(frame)
end

return p