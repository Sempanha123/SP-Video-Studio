import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Commands 1.0
import "../theme"
import "../components"

Popup {
    id: root
    width: Math.min(680, parent ? parent.width - 48 : 680)
    height: Math.min(520, parent ? parent.height - 80 : 520)
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    padding: 0
    background: Rectangle {
        radius: Theme.radius.card
        color: Theme.colors.surface
        border.color: Theme.colors.borderStrong
    }

    property var results: []
    signal commandChosen(string commandId)

    function refresh() {
        results = Commands.search(searchField.text)
    }

    onOpened: {
        Commands.setModalOpen(true)
        searchField.text = ""
        refresh()
        searchField.forceActiveFocus()
    }
    onClosed: Commands.setModalOpen(false)

    contentItem: ColumnLayout {
        spacing: 0
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 58
            color: "transparent"
            RowLayout {
                anchors.fill: parent
                anchors.margins: Theme.spacing.md
                spacing: Theme.spacing.sm
                Text {
                    text: "›"
                    color: Theme.colors.accent
                    font.pixelSize: 25
                    font.family: Theme.type.family
                }
                TextField {
                    id: searchField
                    Layout.fillWidth: true
                    placeholderText: "Search commands…  split, voice, subtitle, export"
                    selectByMouse: true
                    background: null
                    color: Theme.colors.textPrimary
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.body
                    onTextChanged: root.refresh()
                    Keys.onDownPressed: commandList.incrementCurrentIndex()
                    Keys.onUpPressed: commandList.decrementCurrentIndex()
                    Keys.onReturnPressed: {
                        if (commandList.currentIndex >= 0 && commandList.currentIndex < root.results.length) {
                            var item = root.results[commandList.currentIndex]
                            root.commandChosen(item.id)
                            Commands.trigger(item.id)
                            root.close()
                        }
                    }
                }
                Text {
                    text: "Esc"
                    color: Theme.colors.textMuted
                    font.family: Theme.type.family
                    font.pixelSize: Theme.type.caption
                }
            }
        }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.colors.border }

        ListView {
            id: commandList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.results
            currentIndex: root.results.length ? 0 : -1
            reuseItems: true
            delegate: ItemDelegate {
                required property var modelData
                width: commandList.width
                height: 52
                highlighted: ListView.isCurrentItem
                onClicked: {
                    root.commandChosen(modelData.id)
                    Commands.trigger(modelData.id)
                    root.close()
                }
                contentItem: RowLayout {
                    spacing: Theme.spacing.md
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text {
                            Layout.fillWidth: true
                            text: modelData.name
                            color: Theme.colors.textPrimary
                            font.family: Theme.type.family
                            font.pixelSize: Theme.type.body
                            elide: Text.ElideRight
                        }
                        Text {
                            Layout.fillWidth: true
                            text: modelData.category + " · " + modelData.description
                            color: Theme.colors.textMuted
                            font.family: Theme.type.family
                            font.pixelSize: Theme.type.caption
                            elide: Text.ElideRight
                        }
                    }
                    Rectangle {
                        visible: String(modelData.shortcut || "").length > 0
                        radius: 6
                        color: Theme.colors.surfaceRaised
                        border.color: Theme.colors.border
                        implicitWidth: shortcutLabel.implicitWidth + 14
                        implicitHeight: 26
                        Text {
                            id: shortcutLabel
                            anchors.centerIn: parent
                            text: modelData.shortcut || ""
                            color: Theme.colors.textSecondary
                            font.family: Theme.type.family
                            font.pixelSize: Theme.type.caption
                        }
                    }
                }
            }
            ScrollBar.vertical: ScrollBar {}
        }
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 34
            color: Theme.colors.surfaceRaised
            Text {
                anchors.centerIn: parent
                text: "↑ ↓ navigate  ·  Enter run  ·  Esc close"
                color: Theme.colors.textMuted
                font.family: Theme.type.family
                font.pixelSize: Theme.type.caption
            }
        }
    }
}
