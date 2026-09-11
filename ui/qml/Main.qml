import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "theme"
import "components"

ApplicationWindow {
    id: window
    width: 1360
    height: 860
    minimumWidth: 1100
    minimumHeight: 700
    visible: true
    title: "SP Video Studio"
    color: Theme.colors.background

    property string currentPage: "home"
    property string selectedWorkflow: "news"

    function pageTitle(key) {
        var names = { home: "Home", create: "Create", projects: "Projects", batch: "Batch", voices: "Voices", templates: "Templates", assets: "Assets", models: "Models", settings: "Settings" }
        return names[key] || "SP Video Studio"
    }
    function pageSource(key) {
        var sources = { home: "pages/HomePage.qml", create: "pages/CreatePage.qml", projects: "pages/ProjectsPage.qml", batch: "pages/BatchPage.qml", voices: "pages/VoicesPage.qml", templates: "pages/TemplatesPage.qml", assets: "pages/AssetsPage.qml", models: "pages/ModelsPage.qml", settings: "pages/SettingsPage.qml" }
        return Qt.resolvedUrl(sources[key] || sources.home)
    }
    function navigate(page, workflow) {
        currentPage = page
        if (workflow) selectedWorkflow = workflow
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.colors.background

        RowLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.preferredWidth: window.width < 1250 ? 204 : 220
                Layout.fillHeight: true
                color: Theme.colors.sidebar
                border.color: Theme.colors.border

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: Theme.spacing.md
                    spacing: Theme.spacing.xs

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 54
                        Layout.leftMargin: Theme.spacing.sm
                        Layout.rightMargin: Theme.spacing.sm
                        spacing: Theme.spacing.md
                        Rectangle {
                            width: 34; height: 34; radius: 11
                            color: Theme.colors.accentSoft
                            Icon { anchors.centerIn: parent; width: 19; height: 19; name: "spark" }
                        }
                        ColumnLayout { Layout.fillWidth: true; spacing: 0
                            Text { text: "SP Video Studio"; color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.body; font.weight: Theme.type.semibold; elide: Text.ElideRight; Layout.fillWidth: true }
                            Text { text: "Creative desktop"; color: Theme.colors.textMuted; font.family: Theme.type.family; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                    }

                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.colors.border; Layout.topMargin: Theme.spacing.xs; Layout.bottomMargin: Theme.spacing.sm }

                    SidebarItem { Layout.fillWidth: true; text: "Home"; iconName: "home"; selected: window.currentPage === "home"; onClicked: window.navigate("home", "") }
                    SidebarItem { Layout.fillWidth: true; text: "Create"; iconName: "plus-square"; selected: window.currentPage === "create"; onClicked: window.navigate("create", window.selectedWorkflow) }
                    SidebarItem { Layout.fillWidth: true; text: "Projects"; iconName: "projects"; selected: window.currentPage === "projects"; onClicked: window.navigate("projects", "") }
                    SidebarItem { Layout.fillWidth: true; text: "Batch"; iconName: "batch"; selected: window.currentPage === "batch"; onClicked: window.navigate("batch", "") }
                    SidebarItem { Layout.fillWidth: true; text: "Voices"; iconName: "mic"; selected: window.currentPage === "voices"; onClicked: window.navigate("voices", "") }
                    SidebarItem { Layout.fillWidth: true; text: "Templates"; iconName: "template"; selected: window.currentPage === "templates"; onClicked: window.navigate("templates", "") }
                    SidebarItem { Layout.fillWidth: true; text: "Assets"; iconName: "assets"; selected: window.currentPage === "assets"; onClicked: window.navigate("assets", "") }
                    SidebarItem { Layout.fillWidth: true; text: "Models"; iconName: "models"; selected: window.currentPage === "models"; onClicked: window.navigate("models", "") }
                    Item { Layout.fillHeight: true }
                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.colors.border; Layout.bottomMargin: Theme.spacing.sm }
                    SidebarItem { Layout.fillWidth: true; text: "Settings"; iconName: "settings"; selected: window.currentPage === "settings"; onClicked: window.navigate("settings", "") }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 64
                    color: Theme.colors.background
                    border.color: Theme.colors.border
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.spacing.xl
                        anchors.rightMargin: Theme.spacing.xl
                        spacing: Theme.spacing.md
                        Text { text: window.pageTitle(window.currentPage); color: Theme.colors.textPrimary; font.family: Theme.type.family; font.pixelSize: Theme.type.title; font.weight: Theme.type.semibold; Layout.fillWidth: true }
                        RowLayout { spacing: Theme.spacing.sm
                            Rectangle { width: 8; height: 8; radius: 4; color: Theme.colors.success }
                            Text { text: "System ready"; color: Theme.colors.textSecondary; font.family: Theme.type.family; font.pixelSize: Theme.type.caption }
                        }
                        IconButton { iconName: "bell"; tooltip: "Notifications"; onClicked: toast.show("No notifications yet.", "info", 2200) }
                        IconButton { iconName: "settings"; tooltip: "Settings"; onClicked: window.navigate("settings", "") }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Loader {
                        id: pageLoader
                        anchors.fill: parent
                        anchors.margins: Theme.spacing.xl
                        source: window.pageSource(window.currentPage)
                        opacity: status === Loader.Ready ? 1 : 0
                        onLoaded: {
                            if (window.currentPage === "create")
                                item.selectedWorkflow = window.selectedWorkflow
                        }
                        Behavior on opacity { NumberAnimation { duration: Theme.animation.normal } }
                    }
                    Connections {
                        target: pageLoader.item
                        ignoreUnknownSignals: true
                        function onNavigateRequested(page, workflow) { window.navigate(page, workflow) }
                        function onToastRequested(message, variant) { toast.show(message, variant, 3000) }
                    }
                }
            }
        }
    }

    Toast {
        id: toast
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.spacing.xl
    }
}
